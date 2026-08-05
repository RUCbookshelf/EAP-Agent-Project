"""v0.9.7-C WU4 Research smoke (established v0.9.4-B subset).

Overview, Data, and System Audit x English desktop / Chinese mobile
(6 renders) against the WU4 isolated stack, reusing the v0.9.7-A matrix's
research_smoke runner. Research code is untouched in v0.9.7-C; this
confirms no regression in the running stack.
"""
from __future__ import annotations

import json
import pathlib
import sys

from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]
V097A_DIR = PROJECT_ROOT / "verification/v0.9.7-a/v0.9.7-a-20260804-r1"
WU5_DIR = PROJECT_ROOT / "verification/v0.9.7-b/v0.9.7-b-wu5-20260805-r1"
WU6_DIR = PROJECT_ROOT / "verification/v0.9.7-b/v0.9.7-b-wu6-20260805-r1"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(V097A_DIR))
sys.path.insert(0, str(WU6_DIR))
sys.path.insert(0, str(WU5_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

import w6_harness as harness  # noqa: E402
import w5_harness as _w5  # noqa: E402
import v097a_browser_matrix as v097a  # noqa: E402

_w5._base.RUN_DIR = HERE
_w5._base.ISOLATED_DB = HERE / "isolated" / "writing_feedback_v097c_wu4.db"
_w5._base.LOG_DIR = HERE / "logs"
_w5.RUN_DIR = HERE
_w5.ISOLATED_DB = _w5._base.ISOLATED_DB
_w5.LOG_DIR = HERE / "logs"
harness.RUN_DIR = HERE
harness.ISOLATED_DB = _w5.ISOLATED_DB
harness.LOG_DIR = HERE / "logs"

v097a.harness = harness


def main() -> int:
    harness.prepare_isolated_db()
    api = streamlit = None
    evidence: dict = {"run_id": "v0.9.7-c-wu4-research-smoke"}
    try:
        api, streamlit = harness.start_stack("w4_research")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                evidence["research_smoke"] = v097a.research_smoke(
                    browser, "research")
            finally:
                browser.close()
    finally:
        harness.stop_stack(api, streamlit)
    evidence["ports_cleaned"] = True
    (HERE / "research_smoke_evidence.json").write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
    assert len(evidence["research_smoke"]) == 6
    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
