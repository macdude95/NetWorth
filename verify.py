#!/usr/bin/env python3
"""
Browser verification script for Net Worth Dashboard.
Uses Playwright to load the page in headless Chromium, check for JS errors,
capture screenshots, and verify all charts render.
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
        page.wait_for_timeout(2000)  # Wait for Chart.js to load + charts to render
        
        # Check canvas elements exist
        canvases = page.locator("canvas")
        canvas_count = canvases.count()
        print(f"Canvas elements found: {canvas_count}")
        
        if canvas_count < 3:
            errors.append(f"Expected 3 canvases, found {canvas_count}")
        
        # Screenshot full page
        page.screenshot(path=os.path.join(OUTPUT_DIR, "full-page.png"), full_page=True)
        
        # Check each chart renders (has non-zero dimensions)
        for i in range(canvas_count):
            canvas = canvases.nth(i)
            box = canvas.bounding_box()
            if box and box['width'] > 0 and box['height'] > 0:
                print(f"  Canvas {i}: {box['width']:.0f}x{box['height']:.0f} ✓")
            else:
                errors.append(f"Canvas {i} has zero dimensions")
        
        # Verify DATA object exists (scoped as const, check via eval)
        try:
            data = page.evaluate("() => { try { return DATA; } catch(e) { return null; } }")
            if data:
                print(f"DATA loaded: {len(data['series']['dates'])} snapshots, password_enabled={data['password_enabled']}")
            else:
                print("DATA not on window (const scoped) — charts rendered fine regardless")
        except Exception as e:
            print(f"DATA check: {e} (expected — const scoped, not window global)")
        
        # Verify Chart instances exist via getChart
        try:
            charts = page.evaluate("() => { const ids = ['chartNetWorth', 'chartProjections', 'chartStacked']; return ids.map(id => { try { const c = Chart.getChart(document.getElementById(id)); return c ? c.config.type : null; } catch(e) { return null; } }); }")
            print(f"Chart instances: {charts}")
            for i, (id, ctype) in enumerate(zip(['Net Worth', 'Projections', 'Retirement'], charts)):
                if ctype:
                    print(f"  Chart '{id}': type={ctype} ✓")
                else:
                    errors.append(f"Chart '{id}' not rendered")
                    print(f"  Chart '{id}': NOT RENDERED ✗")
        except Exception as e:
            errors.append(f"Chart verification failed: {e}")
        
        browser.close()
    
    # Report
    print(f"\n{'='*50}")
    if errors:
        print(f"❌ {len(errors)} issues found:")
        for e in errors:
            print(f"   - {e}")
        return 1
    else:
        print(f"✅ All charts verified. Screenshots saved to {OUTPUT_DIR}")
        return 0


if __name__ == "__main__":
    sys.exit(verify())
