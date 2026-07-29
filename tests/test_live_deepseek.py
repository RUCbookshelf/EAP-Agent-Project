import os

import pytest

from scripts.verify_live_deepseek import run_live_verification


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_LLM_TESTS") != "1",
    reason="Live DeepSeek test is opt-in; set RUN_LIVE_LLM_TESTS=1.",
)


def test_live_deepseek_uses_structured_history_on_second_submission(tmp_path):
    report = run_live_verification(tmp_path / "live-test.db")
    assert report["status"] == "PASS"
    assert report["provider"] == "deepseek"
    assert report["second_request_history_evidence_count"] >= 1
    assert report["returned_history_evidence_ids"]
    assert report["validation_status"] == "passed"
    assert report["fallback"] is False

