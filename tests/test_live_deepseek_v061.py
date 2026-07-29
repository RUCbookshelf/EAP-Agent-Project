import os

import pytest

from scripts.verify_live_deepseek_v061 import verify


@pytest.mark.skipif(os.getenv("RUN_LIVE_LLM_TESTS") != "1", reason="Live provider test is explicitly opt-in.")
def test_real_deepseek_first_draft_calibration_without_fallback():
    result = verify(write_report=False)
    assert result["status"] == "PASS"
    assert result["provider"] == "deepseek"
    assert result["validation_status"] == "passed"
    assert result["fallback"] is False
    assert result["bias_selected"] is False
    assert result["api_key_recorded"] is False
