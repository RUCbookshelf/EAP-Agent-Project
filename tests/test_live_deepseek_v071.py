from __future__ import annotations

import os

import pytest

from scripts.verify_live_deepseek_v071 import run_live_verification


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_LLM_TESTS") != "1",
    reason="Set RUN_LIVE_LLM_TESTS=1 for the explicit quota-consuming v0.7.1 DeepSeek verification.",
)


def test_live_a_b_c_deepseek_reliability_contracts():
    report = run_live_verification()
    assert set(report) == {"live_a", "live_b", "live_c"}
