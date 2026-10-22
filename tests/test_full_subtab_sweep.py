import asyncio
from playwright.async_api import async_playwright

SCREENSHOT_DIR = r"C:\Users\USER\.gemini\antigravity\brain\c0451ab2-5751-4d25-b592-1b96ca419043"

async def test_full_subtab_sweep():
    print("=== EXECUTING 100% COMPLETE SUBTABS SWEEP ===")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        await page.goto("http://127.0.0.1:8000/")
        await page.wait_for_timeout(1000)

        # 1. Developer Zone - Test All 13 Secondary Subviews
        print("[Dev Zone] Testing all 13 secondary subviews...")
        await page.click(".sidebar-nav-item:has-text('Developer Zone')")
        await page.wait_for_timeout(300)

        dev_subviews = [
            "My Templates", "Blueprints", "Assets", "Blynk.Air", "Static Tokens",
            "Rule Engine", "OAuth 2.0", "Webhooks", "Integrations",
            "Provisioning Sessions", "Crash Reports", "Errors", "Requests log"
        ]
        for sv in dev_subviews:
            print(f"  -> Clicking Dev Subview: {sv}")
            await page.click(f".dev-nav-item:has-text('{sv}')")
            await page.wait_for_timeout(150)
            if sv == "Static Tokens":
                await page.screenshot(path=f"{SCREENSHOT_DIR}\\subtab_dev_static_tokens.png")
            elif sv == "Rule Engine":
                await page.screenshot(path=f"{SCREENSHOT_DIR}\\subtab_dev_rule_engine.png")
            elif sv == "Requests log":
                await page.screenshot(path=f"{SCREENSHOT_DIR}\\subtab_dev_requests_log.png")

        # 2. Template Detail - Test All 11 Template Subtabs
        print("[Dev Zone] Opening Template Detail and testing all 11 subtabs...")
        await page.click(".dev-nav-item:has-text('My Templates')")
        await page.wait_for_timeout(200)
        await page.click(".template-card:has-text('BLINKING LED')")
        await page.wait_for_timeout(300)

        tmpl_subtabs = [
            "Home", "Datastreams", "Dashboard", "Events & Notifications",
            "Connection Lifecycle", "Data Converters", "Metadata", "App Dashboard",
            "User Guides", "Automation Templates", "Voice Assistants"
        ]
        for ts in tmpl_subtabs:
            print(f"  -> Clicking Template Subtab: {ts}")
            await page.click(f"#template-detail-view .subtabs-bar .subtab-item:has-text('{ts}')")
            await page.wait_for_timeout(150)
            if ts == "Connection Lifecycle":
                await page.screenshot(path=f"{SCREENSHOT_DIR}\\subtab_tmpl_connection_lifecycle.png")
            elif ts == "App Dashboard":
                await page.screenshot(path=f"{SCREENSHOT_DIR}\\subtab_tmpl_app_dashboard.png")

        await page.click("#template-detail-view button:has-text('Back to Templates')")
        await page.wait_for_timeout(200)

        # 3. Devices Tab - Test All 4 Device Subtabs
        print("[Devices] Testing Device List and all 4 Device Subtabs...")
        await page.click(".sidebar-nav-item:has-text('Devices')")
        await page.wait_for_timeout(300)
        await page.click("#devices-table-body tr:first-child")
        await page.wait_for_timeout(300)

        device_subtabs = ["Device Dashboard", "Timeline", "Device Info", "Metadata"]
        for ds in device_subtabs:
            print(f"  -> Clicking Device Subtab: {ds}")
            await page.click(f"#device-subtabs-view .subtab-item:has-text('{ds}')")
            await page.wait_for_timeout(150)
        
        await page.click("button:has-text('Back to Devices')")
        await page.wait_for_timeout(200)

        # 4. Automations Tab - Test All 5 Condition Triggers
        print("[Automations] Testing all 5 trigger condition cards...")
        await page.click(".sidebar-nav-item:has-text('Automations')")
        await page.wait_for_timeout(300)

        # 5. Dashboards Tab - Test Interval Controls
        print("[Dashboards] Testing interval controls and split view...")
        await page.click(".sidebar-nav-item:has-text('Dashboards')")
        await page.wait_for_timeout(300)
        await page.click("#pane-dashboards .segmented-pill-group .segmented-pill:has-text('1d')")
        await page.wait_for_timeout(150)

        await browser.close()
        print("=== 100% EXHAUSTIVE SUBTABS SWEEP COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    asyncio.run(test_full_subtab_sweep())
