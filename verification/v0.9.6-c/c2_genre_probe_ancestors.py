"""C2 follow-up 2: ancestor chains for broken icon spans + full icon-class rules."""
from __future__ import annotations

import json, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path
import requests

ROOT = Path(r"A:\EAP Agent Project\writing-feedback-mvp")
OUT = ROOT / "verification" / "v0.9.6-c"
VENV_PY = ROOT / ".venv" / "Scripts" / "python.exe"
TMP = Path(tempfile.mkdtemp(prefix="v096c2-anc-"))
env = dict(os.environ)
env["PYTHON_DOTENV_DISABLED"] = "1"
env.pop("DATABASE_URL", None)
env["DATABASE_PATH"] = str(TMP / "anc.db")
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


def main():
    evidence = {}
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

            evidence["broken_spans"] = page.evaluate("""() => {
                const out = [];
                const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                let node;
                while ((node = walker.nextNode())) {
                    if (node.parentElement && ['STYLE','SCRIPT'].includes(node.parentElement.tagName)) continue;
                    const txt = (node.textContent || '').trim();
                    if (txt.includes('_') && txt.length < 60) {
                        const el = node.parentElement;
                        const chain = [];
                        let cur = el;
                        for (let i = 0; i < 6 && cur; i++) {
                            chain.push({tag: cur.tagName, testid: cur.getAttribute('data-testid'), class_: cur.className});
                            cur = cur.parentElement;
                        }
                        out.push({text: txt, class: el.className, chain: chain});
                    }
                }
                return out;
            }""")

            evidence["icon_class_rules"] = page.evaluate("""() => {
                const rules = [];
                for (const sheet of document.styleSheets) {
                    let rr; try { rr = sheet.cssRules; } catch (e) { continue; }
                    for (const rule of rr) {
                        if (rule.selectorText && rule.cssText.toLowerCase().includes('material symbols')) {
                            rules.push(rule.cssText);
                        }
                    }
                }
                return rules;
            }""")

            # Genre selectbox arrow mechanism
            evidence["genre_arrow"] = page.evaluate("""() => {
                const sel = Array.from(document.querySelectorAll('[data-testid="stSelectbox"]'))
                    .find(s => (s.textContent || '').includes('Genre'));
                if (!sel) return null;
                const html = sel.querySelector('[data-baseweb="select"]');
                const svg = sel.querySelectorAll('svg');
                const spans = Array.from(sel.querySelectorAll('span')).map(s => ({text: (s.textContent||'').trim().slice(0,30), class: s.className})).filter(x => x.text);
                return {has_svg: svg.length, svg_count: svg.length, spans: spans};
            }""")
            browser.close()

        with open(OUT / "c2_genre_ancestors.json", "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
        print(json.dumps(evidence, indent=2, sort_keys=True))
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