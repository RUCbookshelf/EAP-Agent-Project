from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.analysis import AnalyzerRegistry, UnavailableAnalyzer, default_metric_registry
from app.analyzer import BasicAnalyzer
from app.api.main import create_app
from app.config import Settings
from app.configuration import ConfigurationCreate, ConfigurationPayload, configuration_hash
from app.database import Database
from app.diagnosis import HeuristicDiagnoser
from app.llm import LocalDemoProvider, ProviderRouter
from app.models import EssaySubmission
from app.services import (
    AdminReanalysisService, ConfigurationService, DashboardService, ReanalysisRequest,
    RevisionService, SubmissionService,
)


def _settings(tmp_path):
    return Settings(
        database_path=tmp_path / "v06.db", llm_provider="local", deepseek_api_key=None,
        deepseek_base_url="https://api.deepseek.com", deepseek_model="deepseek-chat",
    )


def _service(tmp_path):
    settings = _settings(tmp_path)
    repository = Database(settings.database_path); repository.initialize()
    revisions = RevisionService(repository)
    service = SubmissionService(
        repository, BasicAnalyzer(), HeuristicDiagnoser(),
        ProviderRouter(LocalDemoProvider(), LocalDemoProvider()), revision_service=revisions,
    )
    return settings, repository, revisions, service


def _essay(student, text, when, *, source=None, stage="first draft"):
    return EssaySubmission(
        student_id=student, writing_prompt="Should campuses add more quiet study spaces?",
        genre="argumentative essay", draft_stage=stage, timed=False, tool_use="none",
        essay_text=text, submitted_at=when, revision_of_submission_id=source,
    )


def _seed(tmp_path, count=3):
    settings, repository, revisions, service = _service(tmp_path)
    now = datetime(2026, 2, 1, tzinfo=timezone.utc)
    ids = []
    texts = [
        "Campuses need quiet rooms because students need space to focus. Libraries are often crowded.",
        "Campuses need quiet rooms because students need space to focus. For example, libraries are often crowded during examinations.",
        "Campuses need quiet rooms because focused study supports careful work. For example, unused seminar rooms can open during examinations. Therefore, students gain a practical choice.",
    ]
    for index in range(count):
        ids.append(service.submit(_essay("V06-STUDENT", texts[index], now + timedelta(days=index))).essay_id)
    return settings, repository, revisions, service, ids


def _configuration_service(repository):
    analyzers = AnalyzerRegistry([BasicAnalyzer()])
    return ConfigurationService(repository, analyzers, default_metric_registry())


def test_migration_6_creates_active_configuration_and_audit(tmp_path):
    repository = Database(tmp_path / "migration.db"); repository.initialize()
    assert repository.migration_version() == 11
    active = repository.get_active_configuration()
    assert active.version == "config-v0.8.2" and active.status == "active"
    assert len(repository.list_configuration_audit()) == 5


def test_configuration_create_hash_change_note_and_append_only(tmp_path):
    repository = Database(tmp_path / "config.db"); repository.initialize()
    service = _configuration_service(repository)
    payload = ConfigurationPayload(active_analyzer="basic", mattr_window=60)
    created = service.create(ConfigurationCreate(payload=payload, change_note="Increase MATTR window."))
    assert created.status == "draft" and created.parent_version == "config-v0.8.0"
    assert created.content_hash == configuration_hash(payload)
    assert created.change_note == "Increase MATTR window."
    assert len(service.list()) == 6


def test_configuration_validation_activation_single_active_and_rollback(tmp_path):
    repository = Database(tmp_path / "config.db"); repository.initialize()
    service = _configuration_service(repository)
    created = service.create(ConfigurationCreate(
        payload=ConfigurationPayload(active_analyzer="basic", mattr_window=65),
        change_note="Review a larger lexical window.",
    ))
    validated = service.validate(created.configuration_id)
    assert validated.validation_status == "passed" and validated.status == "validated"
    active = service.activate(created.configuration_id)
    assert active.status == "active"
    assert sum(item.status == "active" for item in service.list()) == 1
    rolled = service.rollback(active.configuration_id, reason="Restore reviewed baseline.")
    assert rolled.version == "config-v0.8.2"
    preserved = service.repository.get_configuration(created.configuration_id)
    assert preserved.status == "inactive"
    actions = [item["action"] for item in service.audit()]
    assert {"create", "validate", "activate", "rollback"} <= set(actions)


def test_invalid_or_unavailable_configuration_cannot_activate(tmp_path):
    repository = Database(tmp_path / "config.db"); repository.initialize()
    analyzers = AnalyzerRegistry([
        BasicAnalyzer(), UnavailableAnalyzer("spacy", "spacy-analyzer-v0.4.0", "missing test model")
    ])
    service = ConfigurationService(repository, analyzers, default_metric_registry())
    created = service.create(ConfigurationCreate(
        payload=ConfigurationPayload(active_analyzer="spacy"), change_note="Test unavailable model.",
    ))
    checked = service.validate(created.configuration_id)
    assert checked.validation_status == "failed" and checked.validation_errors
    with pytest.raises(ValueError, match="cannot be activated"):
        service.activate(created.configuration_id)


@pytest.mark.parametrize(
    "changes",
    [
        {"mattr_window": 2}, {"feedback_priority_count": 5},
        {"low_variability_cv": 0.5, "high_variability_cv": 0.2},
    ],
)
def test_configuration_parameter_ranges(changes):
    with pytest.raises(ValidationError):
        ConfigurationPayload(**changes)


def test_registry_interfaces_expose_analyzer_metric_algorithm_and_prompt(tmp_path):
    repository = Database(tmp_path / "config.db"); repository.initialize()
    registry = _configuration_service(repository).registries()
    assert {item["analyzer_id"] for item in registry["analyzers"]} == {"basic"}
    assert "mattr" in {item["metric_id"] for item in registry["metrics"]}
    assert "revision-alignment" in {item["algorithm_id"] for item in registry["algorithms"]}
    assert "feedback-prompt-v0.5.0" in {item["prompt_version"] for item in registry["prompts"]}
    assert all("overall_calf_score" not in json.dumps(item).casefold() for item in registry["metrics"])


def test_dashboard_timeline_inclusion_exclusion_issues_and_limitations(tmp_path):
    _, repository, _, _, ids = _seed(tmp_path)
    result = DashboardService(repository, default_metric_registry()).build("V06-STUDENT", "word_count")
    assert [item["submission_id"] for item in result["timeline"]] == ids
    assert all("included_in_longitudinal" in item and "analyzer_version" in item for item in result["timeline"])
    assert result["comparability_summary"]["included_count"] >= 1
    assert {"direction", "variability", "confidence", "limitations"} <= result["trend_summary"].keys()
    assert isinstance(result["issue_trajectories"], list)
    assert all(item["display_status"] in {"persistent", "recurring", "recently_reduced", "newly_observed", "insufficient_evidence"} for item in result["issue_trajectories"])
    assert any("not ability" in item.casefold() for item in result["limitations"])


def test_dashboard_never_connects_incompatible_analyzer_metric_or_config_versions(tmp_path):
    _, repository, _, _, ids = _seed(tmp_path)
    second = repository.get_latest_analysis_run(ids[1])
    with repository.connect() as connection:
        connection.execute(
            "UPDATE analysis_runs SET analyzer_version='alternate-analyzer-v9', configuration_version='config-v9' WHERE analysis_run_id=?",
            (second["analysis_run_id"],),
        )
        connection.execute(
            """INSERT INTO metric_results(
                analysis_run_id,metric_id,metric_version,value_json,unit,parameters_json,
                analyzer_version,resource_versions_json,verification_status,status,evidence_json,limitations_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (second["analysis_run_id"], "word_count", "9.0.0", "17", "words", "{}",
             "alternate-analyzer-v9", "{}", "automatic_unverified", "available", "[]", "[]"),
        )
    result = DashboardService(repository, default_metric_registry()).build("V06-STUDENT", "word_count")
    keys = {(item["analyzer_version"], item["metric_version"], item["configuration_version"]) for item in result["metric_segments"]}
    assert len(keys) >= 2
    assert all(len({(p["analyzer_version"], p["metric_version"], p["configuration_version"]) for p in item["points"]}) == 1 for item in result["metric_segments"])


def test_revision_group_uses_one_timeline_representative(tmp_path):
    _, repository, _, service = _service(tmp_path)
    now = datetime(2026, 2, 1, tzinfo=timezone.utc)
    first = service.submit(_essay("GROUP-V06", "Quiet rooms help students focus during demanding study tasks.", now))
    revised = service.submit(_essay(
        "GROUP-V06", "Quiet rooms help students focus during demanding study tasks, especially when libraries are crowded.",
        now + timedelta(days=1), source=first.essay_id, stage="final draft",
    ))
    result = DashboardService(repository, default_metric_registry()).build("GROUP-V06")
    flags = {item["submission_id"]: item["included_in_longitudinal"] for item in result["timeline"]}
    assert flags[first.essay_id] is False and flags[revised.essay_id] is True


def test_admin_reanalysis_preview_append_only_and_no_llm_by_default(tmp_path):
    settings, repository, _, service, ids = _seed(tmp_path, count=1)
    configurations = _configuration_service(repository)
    admin = AdminReanalysisService(repository, settings, configurations, service)
    request = ReanalysisRequest(scope_type="submission", scope_id=str(ids[0]), analyzer_id="basic")
    before = len(repository.list_analysis_runs(ids[0]))
    preview = admin.preview(request)
    assert preview["submission_count"] == 1 and preview["llm_requested"] is False
    result = admin.run(request)
    assert result["llm_called"] is False and result["feedback_records"] == []
    assert len(repository.list_analysis_runs(ids[0])) == before + 1


def test_admin_reanalysis_explicit_llm_path_is_separately_confirmed(tmp_path):
    settings, repository, _, service, ids = _seed(tmp_path, count=1)
    admin = AdminReanalysisService(repository, settings, _configuration_service(repository), service)
    with pytest.raises(ValidationError, match="confirm_llm_cost"):
        ReanalysisRequest(scope_type="submission", scope_id=str(ids[0]), call_llm=True)
    result = admin.run(ReanalysisRequest(
        scope_type="submission", scope_id=str(ids[0]), analyzer_id="basic",
        call_llm=True, confirm_llm_cost=True,
    ))
    assert result["llm_called"] is True
    assert result["feedback_records"][0]["provider"] == "local-demo"


@pytest.mark.parametrize("scope_type", ["student", "analysis_run"])
def test_admin_reanalysis_additional_scopes(tmp_path, scope_type):
    settings, repository, _, service, ids = _seed(tmp_path, count=2)
    admin = AdminReanalysisService(repository, settings, _configuration_service(repository), service)
    scope_id = "V06-STUDENT" if scope_type == "student" else repository.get_latest_analysis_run(ids[0])["analysis_run_id"]
    preview = admin.preview(ReanalysisRequest(scope_type=scope_type, scope_id=scope_id, analyzer_id="basic"))
    assert preview["submission_count"] == (2 if scope_type == "student" else 1)


def test_admin_reanalysis_revision_group_appends_snapshots(tmp_path):
    settings, repository, revisions, service = _service(tmp_path)
    now = datetime(2026, 2, 1, tzinfo=timezone.utc)
    first = service.submit(_essay("RE-RG", "Quiet rooms help students focus during study.", now))
    revised = service.submit(_essay(
        "RE-RG", "Quiet rooms help students focus during demanding study periods.",
        now + timedelta(days=1), source=first.essay_id, stage="revised draft",
    ))
    group_id = revised.revision_snapshot.revision_group_id
    before = len(revisions.history(group_id))
    admin = AdminReanalysisService(repository, settings, _configuration_service(repository), service)
    result = admin.run(ReanalysisRequest(scope_type="revision_group", scope_id=group_id, analyzer_id="basic"))
    assert len(result["revision_snapshot_ids"]) == 1
    assert len(revisions.history(group_id)) == before + 1


def test_admin_api_configuration_dashboard_registries_and_reanalysis(tmp_path):
    settings = _settings(tmp_path)
    with TestClient(create_app(settings)) as client:
        now = datetime(2026, 2, 1, tzinfo=timezone.utc)
        submission = client.post("/api/v1/submissions", json=_essay(
            "API-V06", "Campuses should provide quiet rooms because students need focus.", now,
        ).model_dump(mode="json"))
        assert submission.status_code == 201
        essay_id = submission.json()["submission_id"]
        dashboard = client.get("/api/v1/students/API-V06/dashboard?metric_id=word_count")
        assert dashboard.status_code == 200 and dashboard.json()["timeline"]
        listed = client.get("/api/v1/admin/configurations")
        assert listed.status_code == 200 and "deepseek_api_key" not in listed.text.casefold()
        payload = listed.json()["configurations"][0]["payload"]
        payload["active_analyzer"] = "basic"
        created = client.post("/api/v1/admin/configurations", json={
            "payload": payload, "change_note": "API configuration test.",
        })
        assert created.status_code == 201
        config_id = created.json()["configuration_id"]
        assert client.post(f"/api/v1/admin/configurations/{config_id}/validate").json()["validation_status"] == "passed"
        assert client.post(f"/api/v1/admin/configurations/{config_id}/activate").json()["status"] == "active"
        configured_submission = client.post("/api/v1/submissions", json=_essay(
            "API-V06-CONFIG", "A new submission should record the newly active configuration version.",
            now + timedelta(days=1),
        ).model_dump(mode="json"))
        assert configured_submission.json()["analysis"]["configuration_version"] == created.json()["version"]
        rolled = client.post(
            f"/api/v1/admin/configurations/{config_id}/rollback",
            json={"reason": "Return to the prior reviewed configuration."},
        )
        assert rolled.status_code == 200 and rolled.json()["version"] == "config-v0.8.2"
        rollback_submission = client.post("/api/v1/submissions", json=_essay(
            "API-V06-ROLLBACK", "A later submission should record the restored configuration version.",
            now + timedelta(days=2),
        ).model_dump(mode="json"))
        assert rollback_submission.json()["analysis"]["configuration_version"] == "config-v0.8.2"
        assert client.get("/api/v1/admin/algorithms").status_code == 200
        assert client.get("/api/v1/admin/metrics").status_code == 200
        preview = client.post("/api/v1/admin/reanalysis/preview", json={
            "scope_type": "submission", "scope_id": str(essay_id), "analyzer_id": "basic",
        })
        assert preview.status_code == 200 and preview.json()["llm_requested"] is False
        run = client.post("/api/v1/admin/reanalysis/run", json={
            "scope_type": "submission", "scope_id": str(essay_id), "analyzer_id": "basic",
        })
        assert run.status_code == 200 and run.json()["llm_called"] is False
        version = client.get("/api/v1/system/version").json()
        assert version["application_version"] == "0.8.0" and version["active_configuration_version"].startswith("config-v0.8")


def test_sensitive_configuration_fields_never_enter_api_or_database(tmp_path):
    settings = _settings(tmp_path)
    with TestClient(create_app(settings)) as client:
        payload = client.get("/api/v1/admin/configurations").json()["configurations"][0]["payload"]
        payload["deepseek_api_key"] = "synthetic-secret-value"
        response = client.post("/api/v1/admin/configurations", json={
            "payload": payload, "change_note": "Must be rejected.",
        })
        assert response.status_code == 422
        assert "synthetic-secret-value" not in response.text
    repository = Database(settings.database_path)
    with repository.connect() as connection:
        stored = " ".join(row[0] for row in connection.execute("SELECT payload_json FROM configuration_versions"))
    assert "synthetic-secret-value" not in stored and "api_key" not in stored.casefold()
