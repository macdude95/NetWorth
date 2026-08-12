#!/usr/bin/env python3
"""Browser verification for Net Worth Dashboard (Chart.js only)."""

import sys, os
from playwright.sync_api import sync_playwright

HTML_PATH = os.path.expanduser("~/GithubRepos/NetWorth/docs/index.html")
OUTPUT_DIR = os.path.expanduser("~/GithubRepos/NetWorth/test-screenshots")

def verify():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.on("pageerror", lambda err: errors.append(f"PAGE ERROR: {err}"))
        page.goto(f"file://{HTML_PATH}")
        page.wait_for_timeout(1500)

        # Enter password if gate is present
        try:
            if page.locator("#pw-input").count() > 0:
                page.fill("#pw-input", "vesper")
                page.click("#gate button[type='submit']")
                page.wait_for_timeout(1500)
        except:
            pass

        ids = ['chartNetWorth', 'chartProjections', 'chartStacked']
        names = ['Net Worth', 'Projections', 'Retirement']
        for cid, cname in zip(ids, names):
            ok = page.evaluate(f"""() => {{
                const c = Chart.getChart(document.getElementById('{cid}'));
                return !!(c && c.canvas && c.canvas.getBoundingClientRect().height > 10);
            }}""")
            print(f"  Chart '{cname}': {'rendered' if ok else 'NOT RENDERED'} {'✓' if ok else '✗'}")
            if not ok:
                errors.append(f"Chart '{cname}' not rendered")

        page.screenshot(path=os.path.join(OUTPUT_DIR, "full-page.png"), full_page=True)
        browser.close()

    print(f"\n{'='*50}")
    if errors:
        print(f"❌ {len(errors)} issues:")
        for e in errors: print(f"   - {e}")
        return 1
    print(f"✅ All charts verified. Screenshots: {OUTPUT_DIR}")
    return 0

if __name__ == "__main__":
    sys.exit(verify())
