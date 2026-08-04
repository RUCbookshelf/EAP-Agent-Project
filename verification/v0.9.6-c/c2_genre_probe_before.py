"""v0.9.6-C2 follow-up 2 reproduction: all native icon spans on the Writing page + sidebar.

Dumps every element whose text looks like a Material ligature (contains '_'),
with the owning widget testid, classes, computed styles, and matching rules,
plus the full icon-class rule text.
"""
from __future__ import annotations

import json, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path
import requests

ROOT = Path(r"A:\EAP Agent Project\writing-feedback-mvp")
OUT = ROOT / "verification" / "v0.9.6-c"
VENV_PY = ROOT / ".venv" / "Scripts" / "python.exe"
TMP = Path(tempfile.mkdtemp(prefix="v096c2-genre-"))
env = dict(os.environ)
env["PYTHON_DOTENV_DISABLED"] = "1"
env.pop("DATABASE_URL", None)
env["DATABASE_PATH"] = str(TMP / "genre.db")
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


LIGATURE_DUMP = """() => {
    const out = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let node;
    while ((node = walker.nextNode())) {
        if (node.parentElement && ['STYLE','SCRIPT'].includes(node.parentElement.tagName)) continue;
        const txt = (node.textContent || '').trim();
        if (txt.includes('_') && txt.length < 60) {
            const el = node.parentElement;
            const w = el.closest('[data-testid]');
            const cs = getComputedStyle(el);
            const r = el.getBoundingClientRect();
            out.push({
                text: txt,
                tag: el.tagName,
                classes: Array.from(el.classList),
                testid: el.getAttribute('data-testid'),
                owning_widget_testid: w ? w.getAttribute('data-testid') : null,
                owning_widget_class: w ? w.className : null,
                rect: {x: r.x, y: r.y, w: r.width, h: r.height},
                font_family: cs.fontFamily, font_feature: cs.fontFeatureSettings,
                font_variation: cs.fontVariationSettings, font_size: cs.fontSize,
                font_weight: cs.fontWeight, font_style: cs.fontStyle,
                line_height: cs.lineHeight, letter_spacing: cs.letterSpacing,
                text_transform: cs.textTransform, white_space: cs.whiteSpace,
                color: cs.color, opacity: cs.opacity, visibility: cs.visibility,
                display: cs.display, overflow: cs.overflow,
                pseudo_before_content: getComputedStyle(el, '::before').content,
                pseudo_after_content: getComputedStyle(el, '::after').content,
            });
        }
    }
    return out;
}"""

FULL_ICON_RULE = """() => {
    const rules = [];
    for (const sheet of document.styleSheets) {
        let rr; try { rr = sheet.cssRules; } catch (e) { continue; }
        for (const rule of rr) {
            if (rule.selectorText && rule.selectorText.includes('stIconMaterial')) {
                rules.push(rule.cssText);
            }
        }
    }
    return rules;
}"""


def main():
    evidence = {"stage": "v0.9.6-C2", "kind": "c2_genre_before"}
    try:
        if not wait_ready():
            return 2
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto("http://127.0.0.1:8501", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3500)
            # Navigate to Writing
            page.locator('[data-testid="stSidebar"]').get_by_text("Writing", exact=True).first.click()
            page.wait_for_timeout(1800)

            evidence["writing_page_ligature_elements"] = page.evaluate(LIGATURE_DUMP)
            evidence["stIconMaterial_rules"] = page.evaluate(FULL_ICON_RULE)
            page.screenshot(path=str(OUT / "c2_genre_before_writing.png"))

            # The Genre selectbox arrow (comparison control) structure
            evidence["genre_selectbox_arrow"] = page.evaluate("""() => {
                const sel = Array.from(document.querySelectorAll('[data-testid="stSelectbox"]'))
                    .find(s => (s.textContent || '').includes('Genre'));
                if (!sel) return null;
                const svg = sel.querySelector('svg');
                const icons = sel.querySelectorAll('span');
                const r = sel.getBoundingClientRect();
                return {
                    rect: {x: r.x, y: r.y, w: r.width, h: r.height},
                    has_svg: !!svg,
                    svg_outer: svg ? svg.outerHTML.slice(0, 200) : null,
                    span_count: icons.length,
                    span_texts: Array.from(icons).map(i => (i.textContent || '').trim()).filter(Boolean),
                };
            }""")

            # Timed checkbox + Tool use input: outerHTML snippets and icon spans
            for label in ("Timed writing", "Tool use"):
                evidence[label] = page.evaluate("""(label) => {
                    const nodes = Array.from(document.querySelectorAll('label, [data-testid]'));
                    const target = nodes.find(n => (n.textContent || '').trim().startsWith(label));
                    if (!target) return null;
                    const ctl = target.closest('[data-testid="stCheckbox"], [data-testid="stTextInput"], [data-testid="stSelectbox"]');
                    const icons = ctl ? ctl.querySelectorAll('span[data-testid="stIconMaterial"], span') : [];
                    const out = [];
                    for (const icon of icons) {
                        const txt = (icon.textContent || '').trim();
                        if (!txt) continue;
                        const cs = getComputedStyle(icon);
                        const r = icon.getBoundingClientRect();
                        out.push({text: txt, class: icon.className, font: cs.fontFamily, feature: cs.fontFeatureSettings, rect: {x: r.x, y: r.y, w: r.width, h: r.height}, parent_testid: icon.parentElement ? icon.parentElement.getAttribute('data-testid') : null});
                    }
                    return {widget_testid: ctl ? ctl.getAttribute('data-testid') : null, widget_html: ctl ? ctl.outerHTML.slice(0, 600) : null, icons: out};
                }""", label)
            browser.close()

        with open(OUT / "c2_genre_before.json", "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
        print("WRITING_PAGE_LIGATURES:")
        for item in evidence.get("writing_page_ligature_elements", []):
            print("  ", item["text"], "| widget:", item["owning_widget_testid"], "| font:", item["font_family"][:60], "| rect:", item["rect"])
        print("STICON_RULES:", json.dumps(evidence.get("stIconMaterial_rules"), indent=1)[:800])
        return 0
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