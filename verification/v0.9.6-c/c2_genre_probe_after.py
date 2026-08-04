"""v0.9.6-C2 follow-up 2 AFTER probe: sidebar + Writing Genre expander icons.

Verifies the source-level common fix (stIconMaterial spans excluded from the
pixel body-font rule) in the real rendered app:
- sidebar left/right icons in normal/hover/focus states;
- both Genre-area expander chevrons (keyboard_arrow_right) in normal/hover/
  focus/open states with the Material Symbols icon font;
- no remaining body-font literal ligature text anywhere on the page;
- Genre selectbox (SVG comparison control) unchanged;
- values selectable/retained (Timed checkbox, Tool use input);
- desktop and narrow viewports; icon font resource loaded.
"""
from __future__ import annotations

import json, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path
import requests

ROOT = Path(r"A:\EAP Agent Project\writing-feedback-mvp")
OUT = ROOT / "verification" / "v0.9.6-c"
VENV_PY = ROOT / ".venv" / "Scripts" / "python.exe"
TMP = Path(tempfile.mkdtemp(prefix="v096c2-genre-after-"))
env = dict(os.environ)
env["PYTHON_DOTENV_DISABLED"] = "1"
env.pop("DATABASE_URL", None)
env["DATABASE_PATH"] = str(TMP / "genre_after.db")
env["LLM_PROVIDER"] = "local"
api = subprocess.Popen([str(VENV_PY), "-m", "uvicorn", "app.api.main:app", "--host", "127.0.0.1", "--port", "8000"], cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
st = subprocess.Popen([str(VENV_PY), "-m", "streamlit", "run", "streamlit_app.py", "--server.headless", "true", "--server.port", "8501", "--browser.gatherUsageStats", "false"], cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def wait_ready():
    for _ in range(120):
        try:
            if requests.get("http://127.0.0.1:8000/api/v1/system/health", timeout=1).status_code == 200 and requests.get("http://127.0.0.1:8501", timeout=1).status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


STYLE_FIELDS = [
    "fontFamily", "fontFeatureSettings", "fontVariationSettings", "fontWeight",
    "fontStyle", "fontSize", "lineHeight", "letterSpacing", "textTransform",
    "whiteSpace", "color", "opacity", "visibility", "display", "overflow",
]

ICON_DUMP = """(el) => {
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    const rules = [];
    for (const sheet of document.styleSheets) {
        let rr; try { rr = sheet.cssRules; } catch (e) { continue; }
        for (const rule of rr) {
            if (rule.selectorText && el.matches(rule.selectorText)) {
                rules.push(rule.cssText);
            }
        }
    }
    return {
        tag: el.tagName,
        text: (el.textContent || '').trim(),
        classes: Array.from(el.classList),
        testid: el.getAttribute('data-testid'),
        role: el.getAttribute('role'),
        aria_label: el.getAttribute('aria-label'),
        rect: {x: r.x, y: r.y, w: r.width, h: r.height},
        font_family: cs.fontFamily, font_feature: cs.fontFeatureSettings,
        font_variation: cs.fontVariationSettings, font_weight: cs.fontWeight,
        font_style: cs.fontStyle, font_size: cs.fontSize, line_height: cs.lineHeight,
        letter_spacing: cs.letterSpacing, text_transform: cs.textTransform,
        white_space: cs.whiteSpace, color: cs.color, opacity: cs.opacity,
        visibility: cs.visibility, display: cs.display, overflow: cs.overflow,
        pseudo_before: getComputedStyle(el, '::before').content,
        pseudo_after: getComputedStyle(el, '::after').content,
        matching_rules: rules,
        ancestor_chain: (() => {
            const chain = [];
            let cur = el;
            for (let i = 0; i < 5 && cur; i++) {
                chain.push({tag: cur.tagName, testid: cur.getAttribute('data-testid'), class_: cur.className});
                cur = cur.parentElement;
            }
            return chain;
        })(),
    };
}"""

LIGATURE_SCAN = """() => {
    const out = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let node;
    while ((node = walker.nextNode())) {
        if (node.parentElement && ['STYLE','SCRIPT'].includes(node.parentElement.tagName)) continue;
        const txt = (node.textContent || '').trim();
        if (txt.includes('_') && txt.length < 60) {
            const el = node.parentElement;
            out.push({text: txt, font_family: getComputedStyle(el).fontFamily});
        }
    }
    return out;
}"""

FONTS_LOADED = """() => {
    return {
        check_16: document.fonts.check('16px "Material Symbols Rounded"'),
        check_24: document.fonts.check('24px "Material Symbols Rounded"'),
        families: Array.from(document.fonts).map(f => f.family),
    };
}"""


def main():
    evidence = {"stage": "v0.9.6-C2", "kind": "c2_genre_after"}
    failures = []
    try:
        if not wait_ready():
            return 2
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto("http://127.0.0.1:8501", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3500)
            page.locator('[data-testid="stSidebar"]').get_by_text("Writing", exact=True).first.click()
            page.wait_for_timeout(1800)

            evidence["fonts_loaded"] = page.evaluate(FONTS_LOADED)
            evidence["ligature_elements"] = page.evaluate(LIGATURE_SCAN)
            evidence["expander_count"] = page.locator('div[data-testid="stExpander"]').count()

            # --- Genre selectbox (comparison control, must stay unchanged) ---
            evidence["genre_selectbox"] = page.evaluate("""() => {
                const sel = Array.from(document.querySelectorAll('[data-testid="stSelectbox"]'))
                    .find(s => (s.textContent || '').includes('Genre'));
                if (!sel) return null;
                const svg = sel.querySelector('svg');
                const body = sel.querySelector('[data-baseweb="select"]');
                const r = sel.getBoundingClientRect();
                return {
                    rect: {x: r.x, y: r.y, w: r.width, h: r.height},
                    has_svg: !!svg,
                    svg_path: svg ? (svg.querySelector('path') ? svg.querySelector('path').getAttribute('d') || '' : '').slice(0, 120) : null,
                    material_spans: sel.querySelectorAll('span[data-testid="stIconMaterial"]').length,
                    body_font: body ? getComputedStyle(body).fontFamily : null,
                };
            }""")
            page.locator('div[data-testid="stSelectbox"]').filter(has_text="Genre").first.screenshot(path=str(OUT / "c2_genre_after_genre_selectbox.png"))
            evidence["genre_selectbox_screenshot"] = "c2_genre_after_genre_selectbox.png"

            # --- Expander chevrons: normal / hover / focus / open ---
            expanders = page.locator('div[data-testid="stExpander"]')
            for idx in range(expanders.count()):
                exp = expanders.nth(idx)
                label = exp.locator("summary").first.text_content().strip()
                chevron = exp.locator('summary span[data-testid="stIconMaterial"]').first
                entry = {"label": label}
                entry["summary_role"] = exp.locator("summary").first.get_attribute("role")
                entry["summary_aria"] = exp.locator("summary").first.get_attribute("aria-label")
                entry["normal"] = page.evaluate(ICON_DUMP, chevron.element_handle())
                exp.locator("summary").first.hover()
                page.wait_for_timeout(400)
                entry["hover"] = page.evaluate(ICON_DUMP, chevron.element_handle())
                page.locator("summary").first.focus() if False else exp.locator("summary").first.focus()
                page.wait_for_timeout(300)
                entry["focus"] = page.evaluate(ICON_DUMP, chevron.element_handle())
                # open via click
                exp.locator("summary").first.click()
                page.wait_for_timeout(500)
                entry["open"] = page.evaluate(ICON_DUMP, chevron.element_handle())
                entry["details_open"] = exp.locator("details").first.get_attribute("open") if exp.locator("details").count() else None
                # close via Enter
                exp.locator("summary").first.focus()
                page.keyboard.press("Enter")
                page.wait_for_timeout(400)
                entry["closed_after_enter"] = page.evaluate(ICON_DUMP, chevron.element_handle())
                # open via Space
                page.keyboard.press("Space")
                page.wait_for_timeout(400)
                entry["open_after_space"] = page.evaluate(ICON_DUMP, chevron.element_handle())
                exp.locator("summary").first.click()
                page.wait_for_timeout(400)
                evidence[f"expander_{idx}"] = entry
                shot = "c2_genre_after_timed.png" if "iming" in label or "imed" in label else "c2_genre_after_tool_use.png"
                exp.screenshot(path=str(OUT / shot))
                entry["screenshot"] = shot
                if "Material Symbols Rounded" not in (entry["normal"]["font_family"] or ""):
                    failures.append(f"expander {idx} ({label}) normal font is not Material Symbols: {entry['normal']['font_family']}")
                for state in ("hover", "focus", "open", "closed_after_enter", "open_after_space"):
                    if "Material Symbols Rounded" not in (entry[state]["font_family"] or ""):
                        failures.append(f"expander {idx} ({label}) {state} font is not Material Symbols: {entry[state]['font_family']}")

            # --- sidebar expanded: normal / hover / focus ---
            sb = {}
            left_icon = page.locator('[data-testid="stSidebarCollapseButton"] span[data-testid="stIconMaterial"]').first
            sb["expanded_normal"] = page.evaluate(ICON_DUMP, left_icon.element_handle())
            page.locator('[data-testid="stSidebar"]').hover()
            page.wait_for_timeout(400)
            sb["expanded_hover"] = page.evaluate(ICON_DUMP, left_icon.element_handle())
            page.locator('[data-testid="stSidebarCollapseButton"] button').first.focus()
            page.wait_for_timeout(300)
            sb["expanded_focus"] = page.evaluate(ICON_DUMP, left_icon.element_handle())
            page.screenshot(path=str(OUT / "c2_genre_after_sidebar_expanded.png"))
            sb["expanded_screenshot"] = "c2_genre_after_sidebar_expanded.png"
            # collapse
            page.evaluate("""() => {
                const btn = document.querySelector('[data-testid="stSidebarCollapseButton"] button');
                if (btn) btn.click();
            }""")
            page.wait_for_timeout(1500)
            sb["sidebar_width_collapsed"] = page.evaluate("""() => {
                const s = document.querySelector('[data-testid="stSidebar"]');
                return s ? s.getBoundingClientRect().width : null;
            }""")
            right_icon = page.locator('button[data-testid="stExpandSidebarButton"] span[data-testid="stIconMaterial"]').first
            sb["collapsed_normal"] = page.evaluate(ICON_DUMP, right_icon.element_handle())
            try:
                page.locator('button[data-testid="stExpandSidebarButton"]').first.hover(timeout=3000)
            except Exception:
                pass
            page.wait_for_timeout(400)
            sb["collapsed_hover"] = page.evaluate(ICON_DUMP, right_icon.element_handle())
            page.locator('button[data-testid="stExpandSidebarButton"]').first.focus()
            page.wait_for_timeout(300)
            sb["collapsed_focus"] = page.evaluate(ICON_DUMP, right_icon.element_handle())
            page.locator('button[data-testid="stExpandSidebarButton"]').first.screenshot(path=str(OUT / "c2_genre_after_sidebar_collapsed.png"))
            sb["collapsed_screenshot"] = "c2_genre_after_sidebar_collapsed.png"
            evidence["sidebar"] = sb
            for state in ("expanded_normal", "expanded_hover", "expanded_focus", "collapsed_normal", "collapsed_hover", "collapsed_focus"):
                if "Material Symbols Rounded" not in (sb[state]["font_family"] or ""):
                    failures.append(f"sidebar {state} font is not Material Symbols: {sb[state]['font_family']}")

            # --- value retention: Timed checkbox + Tool use input ---
            page.evaluate("""() => {
                const btn = document.querySelector('button[data-testid="stExpandSidebarButton"]');
                if (btn) btn.click();
            }""")
            page.wait_for_timeout(1500)
            timed_exp = expanders.nth(0)
            timed_exp.locator("summary").first.click()
            page.wait_for_timeout(600)
            cb = timed_exp.locator('input[type="checkbox"]').first
            cb_label = timed_exp.locator('label').filter(has_text='Timed writing').first
            cb_label.scroll_into_view_if_needed()
            cb_label.click(force=True)
            page.wait_for_timeout(1800)
            evidence["timed_checkbox_checked"] = cb.is_checked()
            tools_exp = expanders.nth(1)
            tools_exp.locator("summary").first.click()
            page.wait_for_timeout(600)
            tool_input = tools_exp.locator('input[type="text"]').first
            tool_input.click(force=True)
            page.keyboard.press("Control+A")
            page.keyboard.type("dictionary")
            page.wait_for_timeout(1800)
            evidence["tool_use_value"] = tool_input.input_value()
            if not evidence["timed_checkbox_checked"]:
                failures.append("Timed checkbox did not stay checked after rerun")
            if evidence["tool_use_value"] != "dictionary":
                failures.append("Tool use input value was not retained after rerun")

            page.screenshot(path=str(OUT / "c2_genre_after_writing.png"))
            evidence["writing_screenshot"] = "c2_genre_after_writing.png"

            # --- narrow viewport ---
            page.set_viewport_size({"width": 390, "height": 844})
            page.wait_for_timeout(1200)
            evidence["narrow"] = {"expander_chevrons": []}
            for idx in range(page.locator('div[data-testid="stExpander"]').count()):
                exp = page.locator('div[data-testid="stExpander"]').nth(idx)
                chevron = exp.locator('summary span[data-testid="stIconMaterial"]').first
                d = page.evaluate(ICON_DUMP, chevron.element_handle())
                evidence["narrow"]["expander_chevrons"].append({"label": exp.locator("summary").first.text_content().strip(), "font_family": d["font_family"], "rect": d["rect"]})
                if "Material Symbols Rounded" not in (d["font_family"] or ""):
                    failures.append(f"narrow expander {idx} font is not Material Symbols")
            page.screenshot(path=str(OUT / "c2_genre_after_narrow_writing.png"))
            evidence["narrow_screenshot"] = "c2_genre_after_narrow_writing.png"
            browser.close()

        # --- global no-literal-text check ---
        body_font_ligatures = [e for e in evidence["ligature_elements"] if "Material Symbols Rounded" not in (e.get("font_family") or "")]
        evidence["body_font_ligature_count"] = len(body_font_ligatures)
        if body_font_ligatures:
            failures.append(f"body-font ligature literals remain: {body_font_ligatures}")
        if not evidence["fonts_loaded"]["check_16"] or not evidence["fonts_loaded"]["check_24"]:
            failures.append("Material Symbols Rounded font resource not loaded")

        with open(OUT / "c2_genre_after.json", "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
        print("FAILURES:", json.dumps(failures, indent=1))
        print("LIGATURES:", json.dumps(evidence["ligature_elements"], indent=1))
        print("FONTS:", json.dumps(evidence["fonts_loaded"]))
        return 1 if failures else 0
    finally:
        for proc in (st, api):
            proc.terminate()
        for proc in (st, api):
            try:
                proc.wait(timeout=15)
            except Exception:
                proc.kill()
        shutil.rmtree(TMP, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())