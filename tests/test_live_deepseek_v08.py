from __future__ import annotations

import os

import pytest

from scripts.verify_live_deepseek_v08 import run_live_verification


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_LLM_TESTS") != "1",
    reason="Set RUN_LIVE_LLM_TESTS=1 for the explicit quota-consuming v0.8 DeepSeek verification.",
)


def test_live_a_through_d_calf_contracts():
    report = run_live_verification()
    assert set(report) == {"live_a", "live_b", "live_c", "live_d"}
