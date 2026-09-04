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
        check(
            page.locator("#ttDismissNW").evaluate("el => el.getBoundingClientRect().width >= 44 && el.getBoundingClientRect().height >= 44"),
            "tooltip dismiss button meets touch target size",
        )

        for label in ("3M", "6M", "1Y"):
            page.locator("#timeframeBarNW button", has_text=label).click()
            page.wait_for_timeout(100)
            check(not page_errors and not console_errors, f"Net Worth {label} timeframe switch has no errors")
            page.locator("#timeframeBarStacked button", has_text=label).click()
            page.wait_for_timeout(100)
            check(not page_errors and not console_errors, f"Retirement {label} timeframe switch has no errors")

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

        check(page.locator("#projScenario").count() == 1, "scenario selector renders")
        check(page.locator("#advancedProjection").evaluate("el => !el.open"), "advanced projection settings start collapsed")
        page.locator("#advancedProjection summary").click()
        check(page.locator("#advancedProjection").evaluate("el => el.open"), "advanced projection settings expand")
        page.locator("#projScenario").select_option("conservative")
        check(page.locator("#projGrowth").input_value() == "4", "conservative scenario updates growth")
        page.locator("#projScenario").select_option("expected")
        check(page.locator("#projGrowth").input_value() == "7", "expected scenario updates growth")

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
        page.locator("#advancedProjection summary").click()
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
        check(page.locator(".achievement-card").count() == 6, "achievement category cards render")
        check("complete" in page.locator("#achSummary").inner_text(), "achievement summary renders")
        check(page.locator(".achievement-ladder").count() == 6, "achievement milestone ladders render")
        check(page.locator(".achievement-explainer").count() == 6, "achievement explanations stay compact")
        page.locator(".achievement-explainer").first.locator("summary").click()
        check(page.locator(".achievement-explainer").first.locator("p").is_visible(), "achievement explanation expands")
        check(page.locator(".achievement-ladder-item.current").count() >= 1, "ladder marks current focus clearly")
        check(page.locator(".achievement-ladder-item").first.get_attribute("aria-label"), "ladder states are accessible")
        check(page.locator(".achievement-card").first.locator(".achievement-ladder-item").count() >= 2, "liquid milestones are compacted into a ladder")
        check(page.locator("text=Not projected yet").count() >= 1, "unprojected milestones are clearly labeled")
        check(page.locator("text=20-year bridge").count() >= 1, "bridge ladder includes long runway milestones")
        check(page.locator("text=Age 42").count() >= 1, "retirement target age is displayed")
        check(page.evaluate("DATA.retirement_profile.target_age === 42 && DATA.retirement_profile.birth_year === 1995 && DATA.retirement_profile.birth_month === 9 && !('retirement_access_age' in DATA.retirement_profile)"), "retirement profile is embedded")
        check(page.evaluate("(() => { const m = buildMilestones(projCache).find(x => x.isCoast); const p = DATA.retirement_profile; const months = (p.birth_year + p.target_age - 2026) * 12 + (p.birth_month - 9); const expected = DATA.current.expenses * p.fire_multiple * Math.pow(1 + p.inflation_rate / 100 / 12, months) / Math.pow(1 + (projCache.annualGrowth / 100 / 12), months); return !!m && Math.abs(m.value - expected) < 1; })()"), "Coast FIRE includes inflation")
        check(page.evaluate("(() => { const m = buildMilestones(projCache).find(x => x.name === '5-year bridge'); const p = DATA.retirement_profile; const e = DATA.current.expenses / 12; const r = projCache.annualGrowth / 100 / 12; const i = p.inflation_rate / 100 / 12; const t = (p.birth_year + p.target_age - 2026) * 12 + (p.birth_month - 9); let expected = 0; for (let k = 1; k <= 60; k++) expected += e * Math.pow(1 + i, t + k - 1) / Math.pow(1 + r, t + k); return !!m && Math.abs(m.value - expected) < 1; })()"), "bridge targets use inflation and growth")
        check(page.locator("text=currently covered").count() >= 1 and page.evaluate("Number(DATA.bridgeYearsCovered) > 0"), "bridge estimates years covered")
        check("π million" in page.locator(".achievement-ladder").nth(4).inner_text(), "fun pi milestone renders")
        check("φ million" in page.locator(".achievement-ladder").nth(4).inner_text(), "fun golden ratio milestone renders")
        check(page.locator("text=$1,234,567 liquid").count() >= 1, "fun sequential number milestone renders")
        check(page.evaluate("Math.abs(buildMilestones(projCache).find(x => x.name === 'π million liquid').value - Math.PI * 1000000) < 0.01"), "fun pi milestone uses pi million target")
        check(page.evaluate("Math.abs(buildMilestones(projCache).find(x => x.name === 'φ million liquid').value - ((1 + Math.sqrt(5)) / 2) * 1000000) < 0.01"), "fun golden ratio milestone uses golden ratio target")
        check(page.evaluate("buildMilestones(projCache).find(x => x.name === '$1,234,567 liquid').value === 1234567"), "fun sequential number milestone uses exact target")
        check(page.locator("text=withdrawal rate").count() >= 1, "FIRE milestones explain withdrawal rates")
        check(page.locator("text=Liquid assets exceed mortgage").count() >= 1, "mortgage relationship milestone renders")
        check(page.locator("text=Investments exceed home equity").count() >= 1, "home equity relationship milestone renders")
        check(page.locator(".ach-table").count() == 0, "legacy achievement table is removed")
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
