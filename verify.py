#!/usr/bin/env python3
"""
Browser verification script for Net Worth Dashboard.
Uses Playwright to load the page in headless Chromium, check for JS errors,
capture screenshots, and verify all charts render.
Supports both Chart.js (canvas) and ApexCharts (div/SVG) backends.
"""

import sys
import os
from playwright.sync_api import sync_playwright

HTML_PATH = os.path.expanduser("~/GithubRepos/NetWorth/docs/index.html")
OUTPUT_DIR = os.path.expanduser("~/GithubRepos/NetWorth/test-screenshots")


def verify():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})  # iPhone 14 size
        
        # Capture console errors
        page.on("console", lambda msg: errors.append(f"[{msg.type}] {msg.text}") if msg.type in ("error", "warning") else None)
        page.on("pageerror", lambda err: errors.append(f"PAGE ERROR: {err}"))
        
        page.goto(f"file://{HTML_PATH}")
        page.wait_for_timeout(2500)  # Wait for CDN scripts + chart render
        
        # Determine which library is active
        current_lib = page.evaluate("() => currentLib || 'unknown'")
        print(f"Chart library: {current_lib}")
        
        chart_ids = ['chartNetWorth', 'chartProjections', 'chartStacked']
        chart_names = ['Net Worth', 'Projections', 'Retirement']
        
        for cid, cname in zip(chart_ids, chart_names):
            # Check if the container has rendered content (works for both canvas and SVG/div)
            has_content = page.evaluate(f"""() => {{
                const el = document.getElementById('{cid}');
                if (!el) return false;
                // Check for canvas children (Chart.js) or SVG children (ApexCharts)
                const svg = el.querySelector('svg');
                const canvas = el.querySelector('canvas');
                if (svg) return svg.getBoundingClientRect().height > 10;
                if (canvas) return canvas.getBoundingClientRect().height > 10;
                // Check for ApexCharts instance
                return el.children.length > 0 && el.getBoundingClientRect().height > 10;
            }}""")
            if has_content:
                print(f"  Chart '{cname}': rendered ✓")
            else:
                errors.append(f"Chart '{cname}' not rendered")
                print(f"  Chart '{cname}': NOT RENDERED ✗")
        
        # Screenshot full page
        page.screenshot(path=os.path.join(OUTPUT_DIR, "full-page.png"), full_page=True)
        
        browser.close()
    
    # Report
    print(f"\n{'='*50}")
    if errors:
        print(f"❌ {len(errors)} issues found:")
        for e in errors:
            print(f"   - {e}")
        return 1
    else:
        print(f"✅ All charts verified ({current_lib}). Screenshots saved to {OUTPUT_DIR}")
        return 0


if __name__ == "__main__":
    sys.exit(verify())
