"""v0.9.7-D D1.2 representative rendered comparison (browser).

Real production stack (LLM_PROVIDER=local, isolated DB): seed one complete
priority-derived writing cycle (submission -> feedback priority -> practice
target -> exercise -> attempt -> evaluation -> completed target -> linked
revision) plus one additional active target, then render the redesigned
Student Journey page in English/Chinese x 1280x900/390x844.

Verifies the design-system structure on the real DOM (cycle card head,
stage items, status badges), the sans heading role, no exceptions/overflow/
remote requests/raw keys/unsupported claims, mobile touch targets >= 44px,
and zero writes across all Journey renders. Captures first-implementation
screenshots (before references: verification/v0.9.7-c/wu4 screenshots).
"""
from __future__ import annotations

import json
import pathlib
import sqlite3
import sys

import requests
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]
BASE_HARNESS_DIR = PROJECT_ROOT / "verification/v0.9.4-a/v0.9.4-a-20260801-r1"
WU5_DIR = PROJECT_ROOT / "verification/v0.9.7-b/v0.9.7-b-wu5-20260805-r1"
sys.path.insert(0, str(BASE_HARNESS_DIR))
sys.path.insert(0, str(WU5_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.locale import t  # noqa: E402

import v094a_harness as harness  # noqa: E402
import w5_harness as _w5  # noqa: E402

harness.RUN_DIR = HERE
harness.ISOLATED_DB = HERE / "isolated" / "writing_feedback_v097d_d1.db"
harness.LOG_DIR = HERE / "logs"

SCREENSHOTS = HERE / "screenshots"
RUN_ID = "v0.9.7-d-20260805-r1"
STUDENTS = ("V097D-D1-ED", "V097D-D1-ZD", "V097D-D1-EM", "V097D-D1-ZM")

REPETITION_ESSAY = (
    "People should protect the environment. People should recycle more. "
    "People should save water. People should plant trees. People should reduce waste. "
    "People should use public transport. People should teach children about nature. "
    "People should value clean air."
)
REVISION_ESSAY = (
    "Citizens should protect the environment. Communities can recycle more."
)
VALID_RESPONSE = "A valid response reducing repetition."

FORBIDDEN_WORDING = (
    "mastery", "proficient", "cefr", "learning gain", "improved your writing",
)


def post(path: str, payload: dict) -> dict:
    response = requests.post(f"{harness.BASE}{path}", json=payload, timeout=60)
    assert response.status_code in (200, 201), response.text
    return response.json()


def seed_cycle(student_id: str) -> None:
    essay_id = post("/api/v1/submissions", {
        "student_id": student_id,
        "writing_prompt": "What actions matter for sustainability?",
        "genre": "argumentative essay", "draft_stage": "first draft",
        "timed": False, "tool_use": "none", "essay_text": REPETITION_ESSAY,
    })["submission_id"]
    record = requests.get(
        f"{harness.BASE}/api/v1/submissions/{essay_id}", timeout=60).json()
    priorities = (record.get("feedback") or {}).get("priority_feedback", [])
    index = next(
        i for i, item in enumerate(priorities)
        if item.get("category") == "lexical_repetition")
    target = post("/api/v1/practice-targets", {
        "student_id": student_id, "source_submission_id": essay_id,
        "priority_index": index,
    })
    exercise = post(
        f"/api/v1/practice-targets/{target['practice_target_id']}/exercises",
        {"source_text": REPETITION_ESSAY})
    post(f"/api/v1/exercises/{exercise['exercise_id']}/attempts", {
        "student_id": student_id, "response_text": VALID_RESPONSE,
    })
    post(f"/api/v1/practice-targets/{target['practice_target_id']}/complete", {
        "student_id": student_id,
    })
    post("/api/v1/submissions", {
        "student_id": student_id,
        "writing_prompt": "What actions matter for sustainability?",
        "genre": "argumentative essay", "draft_stage": "revised draft",
        "timed": False, "tool_use": "none", "essay_text": REVISION_ESSAY,
        "revision_of_submission_id": essay_id,
    })
    diagnosis_id = priorities[index]["diagnosis_id"]
    post("/api/v1/practice-targets", {
        "student_id": student_id, "source_submission_id": essay_id,
        "source_diagnosis_id": diagnosis_id,
        "target_code": "lexical_repetition_local",
        "target_label": "Reduce lexical repetition",
        "gate_status": "selected",
    })


def whole_db_counts() -> dict[str, int]:
    with sqlite3.connect(harness.ISOLATED_DB) as con:
        tables = [
            row[0] for row in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
        ]
        return {table: int(con.execute(
            f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]) for table in tables}


def observe(page):
    console_errors, page_errors, remote_requests = [], [], []
    page.on("console", lambda m: console_errors.append(m.text)
            if m.type == "error" else None)
    page.on("pageerror", lambda e: page_errors.append(str(e)))
    page.on("request", lambda r: remote_requests.append(r.url)
            if not r.url.startswith(("http://127.0.0.1", "http://localhost"))
            else None)
    return console_errors, page_errors, remote_requests


def run(browser, student_id: str, lang: str, viewport: dict, tag: str) -> dict:
    context = browser.new_context(viewport=viewport)
    page = context.new_page()
    console_errors, page_errors, remote_requests = observe(page)
    page.goto(harness.UI, timeout=30_000, wait_until="networkidle")
    assert harness.wait_stable(page)
    if lang == "zh_CN":
        assert harness.select_locale(page, lang)
    _w5.open_sidebar(page)
    _w5.click_label(page, t("learning_journey", lang))
    assert harness.wait_stable(page, timeout=20)
    _w5.close_sidebar(page)
    harness.commit_text_input(
        page, ".st-key-journey_student_v2 input", student_id)
    assert harness.wait_stable(page, timeout=30)
    _w5.close_sidebar(page)

    cycle_count = page.locator('[data-testid="px-cycle-head"]').count()
    assert cycle_count == 2
    assert page.locator('[data-testid="px-stage-item"]').count() >= 6
    assert page.locator('[data-testid="px-status-badge"]').count() >= 3
    badges = page.locator('[data-testid="px-status-badge"]')
    states = set(badges.evaluate_all(
        "els => els.map(e => e.getAttribute('data-state'))"))
    assert "success" in states
    assert "neutral" in states or "info" in states
    family = page.evaluate(
        "() => getComputedStyle(document.querySelector('h2.px-page-heading')).fontFamily"
    )
    assert "monospace" not in family.lower()
    assert "cascadia" not in family.lower()
    assert "consolas" not in family.lower()
    # KB-07 / RC-01: only the keyed cycle containers carry the L2 recipe
    # (2px ink border + hard shadow); ancestor blocks stay unframed.
    cycle_border = page.evaluate(
        """() => {
            const el = document.querySelector(
                '[data-testid="stVerticalBlock"][class*="st-key-journey_cycle_"]');
            const s = getComputedStyle(el);
            return [s.borderTopWidth, s.borderTopColor, s.boxShadow];
        }"""
    )
    assert cycle_border[0] == "2px", cycle_border
    assert cycle_border[1] == "rgb(26, 28, 44)", cycle_border
    assert cycle_border[2] != "none", cycle_border
    framed = page.evaluate(
        """() => {
            const els = document.querySelectorAll(
                '[data-testid="stVerticalBlock"]');
            let framed = 0;
            for (const el of els) {
                const s = getComputedStyle(el);
                if (s.borderTopWidth === "2px" && s.boxShadow !== "none") {
                    framed += 1;
                }
            }
            return framed;
        }"""
    )
    assert framed == cycle_count, framed
    stage_border = page.evaluate(
        """() => {
            const el = document.querySelector(
                '[data-testid="stVerticalBlock"][class*="st-key-journey_stage_"]');
            const s = getComputedStyle(el);
            return [s.borderTopWidth, s.borderTopColor];
        }"""
    )
    assert stage_border[0] == "1px", stage_border
    assert stage_border[1] == "rgb(138, 138, 156)", stage_border
    # KB-01: the warning/limitation notice carries a 4px accent bar.
    notice = page.evaluate(
        """() => {
            const el = document.querySelector('.px-notice-warning, .px-notice-info,'
                + ' .px-notice-success');
            if (!el) return null;
            const s = getComputedStyle(el);
            return [s.borderLeftWidth, s.borderLeftColor];
        }"""
    )
    expected_bar = "4px" if viewport["width"] >= 700 else "2px"
    assert notice is not None and notice[0] == expected_bar, notice
    assert notice[1] not in ("rgb(26, 28, 44)", "rgba(0, 0, 0, 0)"), notice
    # KB-02: quiet state label colors actually render on the badge.
    badge = page.evaluate(
        """() => {
            const el = document.querySelector(
                '[data-testid="px-status-badge"][data-state="success"]');
            if (!el) return null;
            const matches = [];
            for (const sheet of document.styleSheets) {
                let rules;
                try { rules = sheet.cssRules; } catch { continue; }
                for (const rule of rules) {
                    if (rule.selectorText && el.matches(rule.selectorText)) {
                        matches.push(rule.selectorText + " -> " + rule.style.color);
                    }
                }
            }
            return {color: getComputedStyle(el).color, matches: matches};
        }"""
    )
    assert badge is not None, badge
    assert badge["color"] == "rgb(20, 83, 45)", badge
    # RC2-01: the primary CTA label renders white (inherits the button's
    # own token color), not ink from the global body-color rule.
    primary_label = page.evaluate(
        """() => {
            const btn = document.querySelector(
                '[data-testid="stBaseButton-primary"]');
            if (!btn) return {error: "no button"};
            const label = btn.querySelector('span, p');
            if (!label) return {error: "no label"};
            const matches = [];
            for (const sheet of document.styleSheets) {
                let rules;
                try { rules = sheet.cssRules; } catch { continue; }
                for (const rule of rules) {
                    if (rule.selectorText && label.matches(rule.selectorText)
                            && rule.style.color) {
                        matches.push(rule.selectorText + " -> " + rule.style.color);
                    }
                }
            }
            return {
                buttonColor: getComputedStyle(btn).color,
                labelColor: getComputedStyle(label).color,
                matches: matches,
            };
        }"""
    )
    assert primary_label is not None, primary_label
    assert primary_label["buttonColor"] == "rgb(255, 255, 255)", primary_label
    assert primary_label["labelColor"] == "rgb(255, 255, 255)", primary_label
    # RC2-03: unavailable/legacy notices keep their dashed border channel.
    dashed = page.evaluate(
        """() => {
            const el = document.querySelector('.px-notice-dashed');
            if (!el) return null;
            const s = getComputedStyle(el);
            return [s.borderTopStyle, s.borderTopWidth];
        }"""
    )
    assert dashed is not None, dashed
    assert dashed[0] == "dashed" and dashed[1] == "2px", dashed
    # RC2-07: the page-title rule is present on the rendered title.
    heading_rule = page.evaluate(
        """() => {
            const el = document.querySelector('h2.px-page-heading');
            const s = getComputedStyle(el);
            return [s.borderBottomStyle, s.borderBottomWidth];
        }"""
    )
    expected_rule = "4px" if viewport["width"] >= 700 else "2px"
    assert heading_rule[0] == "solid", heading_rule
    assert heading_rule[1] == expected_rule, heading_rule
    column = page.evaluate(
        """() => {
            const el = document.querySelector(
                '[data-testid="stMainBlockContainer"]');
            return el ? getComputedStyle(el).maxWidth : null;
        }"""
    )

    exceptions = page.locator('[data-testid="stException"]').count()
    assert page.locator('[data-testid="px-loading"]').count() == 0
    width = page.evaluate("() => window.innerWidth")
    overflow = page.evaluate(
        "() => document.documentElement.scrollWidth") > width
    text = page.locator('[data-testid="stMainBlockContainer"]').inner_text()
    raw_keys = [key for key in ("student_journey_", "journey_", "student_practice_")
                if key in text]
    normalized = text.lower()
    for phrase in ("none establishes learning, mastery, or stable transfer.",
                   "no priority passed the diagnostic gate",
                   "not proof of stable transfer or causation",
                   "not proof that practice caused the later pattern"):
        normalized = normalized.replace(phrase, "")
    forbidden = [word for word in FORBIDDEN_WORDING if word in normalized]
    assert exceptions == 0 and not overflow and not raw_keys and not forbidden

    if viewport["width"] < 700:
        target_selector = (
            '[data-testid="stBaseButton-primary"],'
            ' [data-testid="stBaseButton-secondary"],'
            ' .st-key-journey_student_v2 input'
        )
        targets = page.locator(target_selector)
        for index in range(targets.count()):
            box = targets.nth(index).bounding_box()
            assert box is not None and box["height"] >= 44, \
                (tag, index, box)

    shot = SCREENSHOTS / f"{tag}_journey_design_system.png"
    shot.parent.mkdir(parents=True, exist_ok=True)
    if viewport["width"] < 700:
        sidebar = page.locator('[data-testid="stSidebar"]')
        if sidebar.count() and sidebar.first.get_attribute("aria-expanded") == "true":
            raise RuntimeError("mobile sidebar still open before capture")
    page.screenshot(path=str(shot), full_page=True)
    # RC-02: Streamlit 1.60 scrolls an inner container, not the window.
    # Find the scroller inside the main content block (never the sidebar).
    scroll_probe = """
        () => {
            const out = [];
            for (const e of document.querySelectorAll('*')) {
                const s = getComputedStyle(e);
                if ((s.overflowY === "auto" || s.overflowY === "scroll")
                        && e.scrollHeight > e.clientHeight + 40) {
                    out.push({
                        testid: e.getAttribute("data-testid") || "",
                        cls: (e.getAttribute("class") || "").slice(0, 60),
                        extra: e.scrollHeight - e.clientHeight,
                    });
                }
            }
            return out;
        }
    """
    scrollers = page.evaluate(scroll_probe)
    scroll_script = """
        () => {
            const candidates = [
                document.querySelector('[data-testid="stMain"]'),
            ].filter(Boolean);
            const scroller = candidates.find(
                (e) => e.scrollHeight > e.clientHeight + 120
                    && getComputedStyle(e).overflowY === "auto");
            if (!scroller) return 0;
            scroller.scrollTop = scroller.scrollHeight;
            return scroller.scrollTop;
        }
    """
    scrolled = page.evaluate(scroll_script)
    assert scrolled > 0, (scrolled, scrollers)
    page.wait_for_timeout(500)
    bottom_shot = SCREENSHOTS / f"{tag}_journey_bottom.png"
    page.screenshot(path=str(bottom_shot))
    assert bottom_shot.read_bytes() != shot.read_bytes(), \
        "bottom capture identical to top"
    # RC2-10: a mid-scroll capture evidences two-card cycle separation.
    mid_scrolled = page.evaluate(
        """() => {
            const scroller = document.querySelector('[data-testid="stMain"]');
            if (!scroller) return 0;
            scroller.scrollTop = Math.round(scroller.scrollHeight * 0.45);
            return scroller.scrollTop;
        }"""
    )
    assert mid_scrolled > 0, mid_scrolled
    page.wait_for_timeout(400)
    mid_shot = SCREENSHOTS / f"{tag}_journey_mid.png"
    page.screenshot(path=str(mid_shot))
    assert mid_shot.read_bytes() not in (
        shot.read_bytes(), bottom_shot.read_bytes()), "mid capture duplicate"
    page.evaluate(
        """
        () => {
            const candidates = [
                document.querySelector('[data-testid="stMain"]'),
            ].filter(Boolean);
            const scroller = candidates.find(
                (e) => e.scrollHeight > e.clientHeight + 120
                    && getComputedStyle(e).overflowY === "auto");
            if (scroller) scroller.scrollTop = 0;
        }
        """
    )
    page.wait_for_timeout(200)
    unexpected = [item for item in console_errors
                  if not harness.is_allowed_console(item)]
    result = {
        "combination": f"{lang} {viewport['width']}x{viewport['height']}",
        "cycle_cards": cycle_count,
        "stage_items": page.locator('[data-testid="px-stage-item"]').count(),
        "badge_states": sorted(states),
        "heading_sans": True,
        "main_column_max_width": column,
        "framed_containers": framed,
        "badge_label_color": badge["color"],
        "primary_cta_label_color": primary_label["labelColor"],
        "dashed_border": dashed,
        "page_heading_rule": heading_rule,
        "notice_accent_bar": notice,
        "exceptions": exceptions, "overflow": overflow,
        "raw_keys": raw_keys, "forbidden": forbidden,
        "console_errors": unexpected, "page_errors": page_errors,
        "remote_requests": remote_requests,
        "screenshot": str(shot.relative_to(PROJECT_ROOT)),
        "bottom_screenshot": str(bottom_shot.relative_to(PROJECT_ROOT)),
        "mid_screenshot": str(mid_shot.relative_to(PROJECT_ROOT)),
    }
    context.close()
    return result


def main() -> int:
    harness.prepare_isolated_db()
    with sqlite3.connect(harness.ISOLATED_DB) as con:
        for student_id in STUDENTS:
            con.execute(
                "INSERT OR IGNORE INTO students (student_id, created_at, "
                "is_synthetic) VALUES (?, '2026-08-05T00:00:00+00:00', 1)",
                (student_id,))
        con.commit()
    api = streamlit = None
    evidence: dict = {"run_id": RUN_ID}
    try:
        api, streamlit = harness.start_stack("d1_matrix")
        for student_id in STUDENTS:
            seed_cycle(student_id)
            seed_cycle(student_id)
        payload = requests.get(
            f"{harness.BASE}/api/v1/students/{STUDENTS[0]}/journey",
            timeout=30).json()
        assert payload["cycles_version"] == "journey-cycle-v0.9.7-c"
        assert len(payload["cycles"]) == 2
        states = {p["activity_state"]
                  for p in payload["cycles"][0]["practice_cycles"]}
        assert states == {"completed", "available"}, states
        evidence["cycle_view"] = {
            "version": payload["cycles_version"],
            "cycle_count": len(payload["cycles"]),
            "practice_states": sorted(states),
        }
        before = whole_db_counts()
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                evidence["en_desktop"] = run(
                    browser, STUDENTS[0], "en",
                    {"width": 1280, "height": 900}, "en_1280x900")
                evidence["zh_desktop"] = run(
                    browser, STUDENTS[1], "zh_CN",
                    {"width": 1280, "height": 900}, "zh_1280x900")
                evidence["en_mobile"] = run(
                    browser, STUDENTS[2], "en",
                    {"width": 390, "height": 844}, "en_390x844")
                evidence["zh_mobile"] = run(
                    browser, STUDENTS[3], "zh_CN",
                    {"width": 390, "height": 844}, "zh_390x844")
            finally:
                browser.close()
        after = whole_db_counts()
        assert before == after
        evidence["journey_reads_zero_writes"] = True
    finally:
        harness.stop_stack(api, streamlit)
    (HERE / "rendered_page_matrix_evidence.json").write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
    for combo in ("en_desktop", "zh_desktop", "en_mobile", "zh_mobile"):
        item = evidence[combo]
        assert not item["console_errors"], item
        assert not item["page_errors"], item
        assert not item["remote_requests"], item
        assert item["exceptions"] == 0 and not item["overflow"]
        assert not item["raw_keys"] and not item["forbidden"]
        assert item["heading_sans"]
        assert item["cycle_cards"] == 2
        assert item["framed_containers"] == 2
    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
