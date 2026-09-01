#!/usr/bin/env python3
"""Browser verification for the Net Worth Dashboard."""

import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

PROJECT_DIR = Path(__file__).resolve().parent
HTML_PATH = PROJECT_DIR / "docs" / "index.html"
OUTPUT_DIR = PROJECT_DIR / "test-screenshots"
PASSWORD = "vesper"


def verify():
    OUTPUT_DIR.mkdir(exist_ok=True)
    failures = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page_errors = []
        console_errors = []
        page.on("pageerror", lambda err: page_errors.append(str(err)))
        page.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error"
            else None,
        )

        page.goto(f"file://{HTML_PATH}")
        page.wait_for_timeout(2500)

        if page.locator("#pw-input").count() > 0:
            page.fill("#pw-input", PASSWORD)
            page.click("#gate button[type='submit']")
            page.wait_for_timeout(500)

        def check(condition, message):
            if not condition:
                failures.append(message)
                print(f"  FAIL: {message}")
            else:
                print(f"  PASS: {message}")

        check(page.locator("#dashboard").is_visible(), "password unlocks dashboard")
        for chart_id, name in (
            ("chartNetWorth", "Net Worth"),
            ("chartProjections", "Projections"),
            ("chartStacked", "Retirement"),
        ):
            rendered = page.evaluate(
                """id => {
                    const canvas = document.getElementById(id);
                    const chart = canvas && Chart.getChart(canvas);
                    return !!(chart && canvas.getBoundingClientRect().height > 10);
                }""",
                chart_id,
            )
            check(rendered, f"{name} chart renders")

        check(
            page.locator("#chartNetWorth").get_attribute("aria-label"),
            "charts have accessible descriptions",
        )
        check(
            page.locator("#ttDismissNW").get_attribute("aria-label"),
            "tooltip dismiss button is accessible",
        )

        page.locator("#timeframeBarNW button", has_text="1Y").click()
        page.wait_for_timeout(200)
        check(not page_errors and not console_errors, "Net Worth timeframe switch has no errors")
        page.locator("#timeframeBarStacked button", has_text="1Y").click()
        page.wait_for_timeout(200)
        check(not page_errors and not console_errors, "Retirement timeframe switch has no errors")

        page.locator("#segPie").click()
        page.wait_for_timeout(200)
        check(
            page.evaluate("!!Chart.getChart(document.getElementById('chartStacked'))"),
            "Pie view renders",
        )
        check(
            page.locator("#timeframeBarStacked").evaluate("el => getComputedStyle(el).display === 'none'"),
            "Pie view removes irrelevant timeframe controls",
        )
        page.locator("#segBar").click()

        page.locator("#projIncome").fill("500")
        page.locator("#projIncome").dispatch_event("input")
        page.wait_for_timeout(200)
        check(
            page.evaluate("!!Chart.getChart(document.getElementById('chartProjections'))"),
            "projection inputs recalculate safely",
        )
        page.reload()
        page.wait_for_timeout(2500)
        page.fill("#pw-input", PASSWORD)
        page.click("#gate button[type='submit']")
        page.wait_for_timeout(500)
        check(page.locator("#projIncome").input_value() == "500", "projection inputs persist locally")
        page.locator("button", has_text="Reset").click()
        check(page.locator("#projIncome").input_value() == "400", "projection inputs reset to defaults")
        page.locator("#projExpenses").fill("0")
        page.locator("#projExpenses").dispatch_event("input")
        page.wait_for_timeout(200)
        check(
            page.locator(".ach-table").count() == 0 or page.locator(".ach-table tr").count() >= 17,
            "zero-expense projection keeps achievements functional",
        )

        page.locator(".ach-toggle").click()
        check(page.locator(".ach-table tr").count() >= 17, "achievement rows render")
        check(page.locator(".stat-box").count() == 4, "stats row includes snapshot count")
        check(
            page.locator(".ach-toggle").get_attribute("aria-expanded") == "true",
            "achievement disclosure state is accessible",
        )

        check(not page_errors, f"no page errors ({page_errors})")
        check(not console_errors, f"no console errors ({console_errors})")
        page.screenshot(path=str(OUTPUT_DIR / "full-page.png"), full_page=True)
        browser.close()

    if failures:
        print(f"\n❌ {len(failures)} verification failures")
        return 1
    print(f"\n✅ Dashboard verified. Screenshot: {OUTPUT_DIR / 'full-page.png'}")
    return 0


if __name__ == "__main__":
    sys.exit(verify())
