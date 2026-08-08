from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from app.config import PROJECT_ROOT, Settings
from scripts import verify_launcher
from scripts.verify_launcher import (
    LauncherIsolationError,
    cleanup_database,
    classify_verify_environment,
    is_development_database,
    is_inside_protected_data,
    is_unsafe_target,
    main,
    provision_temp_database,
)


DEV_DB = PROJECT_ROOT / "data" / "writing_feedback.db"


def make_settings(database_path: Path) -> Settings:
    return Settings(
        database_path=database_path,
        llm_provider="local",
        deepseek_api_key=None,
        deepseek_base_url="https://api.deepseek.com",
        deepseek_model="deepseek-chat",
    )


def step_modules(calls):
    return [c[c.index("-m") + 1] for c in calls]


@pytest.fixture(autouse=True)
def clean_db_env(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_PATH", raising=False)
    monkeypatch.setenv("WRITING_FEEDBACK_ENV_FILE", str(Path.cwd() / "absent-v096dp0v2.env"))


def test_verify_with_no_database_override_auto_provisions_and_never_uses_dev_db(
    monkeypatch, tmp_path, capsys
):
    calls = []

    def fake_run_step(args, env):
        calls.append(args)
        url = env["DATABASE_URL"]
        path = Path(url.removeprefix("sqlite:///"))
        path.write_bytes(b"fake isolated db")
        return 0

    monkeypatch.setattr(verify_launcher, "run_step", fake_run_step)
    assert main(["--tmp-root", str(tmp_path)]) == 0
    assert step_modules(calls) == [
        "scripts.migrate_database",
        "scripts.initialize_project",
        "scripts.smoke_stack",
    ]
    assert "DATABASE_URL" in os.environ
    effective = Path(os.environ["DATABASE_URL"].removeprefix("sqlite:///"))
    assert effective.is_absolute()
    assert not is_unsafe_target(effective)
    assert effective.parent == tmp_path
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "PASS"
    assert output["isolation_mode"] == "auto_provision"
    assert Path(output["effective_database_path"]) == effective


def test_verify_with_only_database_path_never_falls_back_to_dev_db(
    monkeypatch, tmp_path
):
    calls = []
    monkeypatch.setenv("DATABASE_PATH", str(DEV_DB))

    def fake_run_step(args, env):
        calls.append(args)
        return 0

    monkeypatch.setattr(verify_launcher, "run_step", fake_run_step)
    assert main(["--tmp-root", str(tmp_path)]) == 0
    assert len(calls) == 3
    effective = Path(os.environ["DATABASE_URL"].removeprefix("sqlite:///"))
    assert effective != DEV_DB
    assert not is_unsafe_target(effective)


def test_verify_with_database_url_resolving_to_dev_db_fails_before_startup(
    monkeypatch, tmp_path
):
    def unexpected_run_step(args, env):
        raise AssertionError("no step may start when the target is unsafe")

    monkeypatch.setattr(verify_launcher, "run_step", unexpected_run_step)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{DEV_DB.as_posix()}")
    assert main(["--tmp-root", str(tmp_path)]) == 1


@pytest.mark.parametrize(
    "url_value",
    [
        f"sqlite:///{DEV_DB.as_posix()}",
        "sqlite:///data/writing_feedback.db",
        "sqlite:///data/./writing_feedback.db",
        "sqlite:///data/../data/writing_feedback.db",
        f"sqlite:///{DEV_DB.as_posix().upper()}",
        f"sqlite:///{DEV_DB.as_posix().replace('/', os.sep)}",
    ],
)
def test_equivalent_development_database_paths_are_rejected(monkeypatch, tmp_path, url_value):
    calls = []

    def unexpected_run_step(args, env):
        calls.append(args)
        return 0

    monkeypatch.setattr(verify_launcher, "run_step", unexpected_run_step)
    monkeypatch.setenv("DATABASE_URL", url_value)
    assert main(["--tmp-root", str(tmp_path)]) == 1
    assert calls == []


def test_any_database_inside_protected_data_directory_is_rejected(monkeypatch, tmp_path):
    calls = []

    def unexpected_run_step(args, env):
        calls.append(args)
        return 0

    monkeypatch.setattr(verify_launcher, "run_step", unexpected_run_step)
    monkeypatch.setenv(
        "DATABASE_URL",
        f"sqlite:///{(PROJECT_ROOT / 'data' / 'some_other_isolated.db').as_posix()}",
    )
    assert main(["--tmp-root", str(tmp_path)]) == 1
    assert calls == []
    assert is_unsafe_target(PROJECT_ROOT / "data" / "nested" / "x.db")


def test_valid_isolated_database_url_is_accepted(monkeypatch, tmp_path, capsys):
    calls = []
    isolated = tmp_path / "explicit-isolated.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{isolated.as_posix()}")

    def fake_run_step(args, env):
        calls.append(args)
        Path(env["DATABASE_URL"].removeprefix("sqlite:///")).write_bytes(b"db")
        return 0

    monkeypatch.setattr(verify_launcher, "run_step", fake_run_step)
    assert main(["--tmp-root", str(tmp_path)]) == 0
    assert len(calls) == 3
    output = json.loads(capsys.readouterr().out)
    assert output["isolation_mode"] == "explicit"
    assert Path(output["effective_database_path"]) == isolated
    assert list(tmp_path.glob("wfm-verify-*.db")) == []


def test_auto_provisioned_temporary_database_is_removed_after_completion(
    monkeypatch, tmp_path
):
    created = []

    def fake_run_step(args, env):
        path = Path(env["DATABASE_URL"].removeprefix("sqlite:///"))
        path.write_bytes(b"db")
        Path(str(path) + "-journal").write_bytes(b"j")
        created.append(path)
        return 0

    monkeypatch.setattr(verify_launcher, "run_step", fake_run_step)
    assert main(["--tmp-root", str(tmp_path)]) == 0
    assert len(created) == 3
    assert len(set(created)) == 1
    assert not created[0].exists()
    assert not Path(str(created[0]) + "-journal").exists()
    assert list(tmp_path.glob("wfm-verify-*.db")) == []


def test_temp_database_removed_even_when_a_step_fails(monkeypatch, tmp_path):
    def failing_run_step(args, env):
        path = Path(env["DATABASE_URL"].removeprefix("sqlite:///"))
        path.write_bytes(b"db")
        return 1

    monkeypatch.setattr(verify_launcher, "run_step", failing_run_step)
    assert main(["--tmp-root", str(tmp_path)]) == 1
    assert list(tmp_path.glob("wfm-verify-*.db")) == []


def test_empty_database_url_is_refused_before_startup(monkeypatch, tmp_path):
    calls = []

    def unexpected_run_step(args, env):
        calls.append(args)
        return 0

    monkeypatch.setattr(verify_launcher, "run_step", unexpected_run_step)
    monkeypatch.setenv("DATABASE_URL", "")
    assert main(["--tmp-root", str(tmp_path)]) == 1
    assert calls == []


def test_refusal_message_explains_contract_without_leaking_values(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(verify_launcher, "run_step", lambda args, env: 0)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{DEV_DB.as_posix()}")
    assert main(["--tmp-root", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert "ERROR:" in err
    assert "refused before startup" in err
    assert "temporary" in err
    assert "data/" in err
    assert f"sqlite:///{DEV_DB.as_posix()}" not in err
    assert "DEEPSEEK" not in err.upper()


def test_windows_path_normalization_helpers():
    assert is_development_database(DEV_DB)
    assert is_development_database(PROJECT_ROOT / "DATA" / "Writing_Feedback.DB")
    assert is_development_database(PROJECT_ROOT / "data" / ".." / "data" / "writing_feedback.db")
    assert is_inside_protected_data(PROJECT_ROOT / "data" / "anything.db")
    assert is_inside_protected_data(PROJECT_ROOT / "data")
    assert not is_inside_protected_data(PROJECT_ROOT / "app")
    assert not is_unsafe_target(Path("C:/tmp/isolated.db"))


def test_provision_and_cleanup_helpers(tmp_path):
    provisioned = provision_temp_database(tmp_path)
    provisioned.write_bytes(b"db")
    Path(str(provisioned) + "-journal").write_bytes(b"j")
    Path(str(provisioned) + "-wal").write_bytes(b"w")
    Path(str(provisioned) + "-shm").write_bytes(b"s")
    cleanup_database(provisioned)
    assert not provisioned.exists()
    assert not Path(str(provisioned) + "-journal").exists()
    assert not Path(str(provisioned) + "-wal").exists()
    assert not Path(str(provisioned) + "-shm").exists()


def test_classify_environment_directly():
    safe = make_settings(Path("C:/tmp/isolated.db"))
    plan = classify_verify_environment(None, safe)
    assert plan["mode"] == "auto_provision"
    plan = classify_verify_environment("sqlite:///C:/tmp/x.db", safe)
    assert plan["mode"] == "explicit"
    with pytest.raises(LauncherIsolationError):
        classify_verify_environment("sqlite:///C:/tmp/x.db", make_settings(DEV_DB))
    with pytest.raises(LauncherIsolationError):
        classify_verify_environment("", safe)


def test_env_file_dev_db_default_cannot_block_auto_isolation(monkeypatch, tmp_path):
    # Incident condition: .env points at the development database but the
    # process environment does not set DATABASE_URL; verification must
    # auto-isolate instead of refusing or touching the development database.
    monkeypatch.setenv("WRITING_FEEDBACK_ENV_FILE", str(PROJECT_ROOT / ".env"))
    calls = []

    def fake_run_step(args, env):
        calls.append(args)
        return 0

    monkeypatch.setattr(verify_launcher, "run_step", fake_run_step)
    assert main(["--tmp-root", str(tmp_path)]) == 0
    assert len(calls) == 3
    effective = Path(os.environ["DATABASE_URL"].removeprefix("sqlite:///"))
    assert not is_unsafe_target(effective)


def test_run_bat_verify_branch_guards_before_database_steps():
    run_bat = (PROJECT_ROOT / "run.bat").read_text(encoding="utf-8")
    verify_index = run_bat.index('"%~1"=="--verify"')
    migrate_index = run_bat.index("scripts.migrate_database")
    guard_index = run_bat.index("scripts.verify_launcher")
    assert guard_index < migrate_index
    assert verify_index < migrate_index
    verify_section = run_bat[verify_index : run_bat.index(":start_failed")]
    assert "scripts.migrate_database" not in verify_section
    assert "scripts.initialize_project" not in verify_section
    assert "scripts.run_local" not in verify_section


def test_normal_launcher_behavior_without_verify_is_unchanged():
    run_bat = (PROJECT_ROOT / "run.bat").read_text(encoding="utf-8")
    assert run_bat.index("scripts.migrate_database") < run_bat.index("scripts.initialize_project")
    assert run_bat.index("scripts.initialize_project") < run_bat.index("scripts.run_local")
    assert run_bat.index('"%~1"=="--install-only"') > run_bat.index("scripts.initialize_project")
    # Launcher migration (environment goal): the Python 3.11 failure label was
    # replaced by :bootstrap_failed; verify_launcher must still only appear in
    # the --verify branch, never in the normal startup/failure tail.
    assert "scripts.verify_launcher" not in run_bat[run_bat.rindex(":bootstrap_failed") :]
def test_settings_database_resolution_contract(monkeypatch):
    from app.config import load_settings

    monkeypatch.setenv("WRITING_FEEDBACK_ENV_FILE", str(Path.cwd() / "absent-v096dp0v2.env"))
    monkeypatch.setenv("DATABASE_URL", "sqlite:///C:/tmp/url.db")
    monkeypatch.setenv("DATABASE_PATH", "C:/tmp/path.db")
    assert load_settings().database_path == Path("C:/tmp/url.db")
    monkeypatch.delenv("DATABASE_URL")
    assert load_settings().database_path == Path("C:/tmp/path.db")
    monkeypatch.delenv("DATABASE_PATH")
    assert load_settings().database_path == PROJECT_ROOT / "data" / "writing_feedback.db"
