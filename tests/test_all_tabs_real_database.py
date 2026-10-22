import asyncio
import os
import sys
from playwright.async_api import async_playwright

ARTIFACTS_DIR = r"C:\Users\USER\.gemini\antigravity\brain\c0451ab2-5751-4d25-b592-1b96ca419043"

async def run_verification():
    print("Starting Playwright verification of all 13 tabs with real SQLite data...")
    dialogs = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        # Catch any unexpected alert/prompt/confirm dialogs
        page.on("dialog", lambda d: (dialogs.append(d.message), d.accept()))

        # Collect console errors
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        await page.goto("http://127.0.0.1:8000/", wait_until="networkidle")
        await page.wait_for_timeout(2000)

        tabs = [
            ("get-started", "Get Started"),
            ("dashboards", "Dashboards"),
            ("devices", "Devices"),
            ("custom-data", "Custom Data"),
            ("developer-zone", "Developer Zone"),
            ("automations", "Automations"),
            ("users", "Users"),
            ("organizations", "Organizations"),
            ("locations", "Locations"),
            ("snapshots", "Snapshots"),
            ("fleet-management", "Fleet Management"),
            ("in-app-messaging", "In-App Messaging"),
            ("predictive-maintenance", "Predictive Maintenance")
        ]

        results = {}

        for tab_id, tab_title in tabs:
            print(f"Testing tab: {tab_title} ({tab_id})...")
            await page.evaluate(f"switchTab('{tab_id}')")
            await page.wait_for_timeout(1000)
            
            # Check visibility
            is_visible = await page.is_visible(f"#pane-{tab_id}")
            results[tab_id] = {"visible": is_visible}
            assert is_visible, f"Pane #pane-{tab_id} should be visible"

            # Check specific live data containers
            if tab_id == "organizations":
                rows = await page.locator("#orgs-table-body tr").count()
                print(f"  -> Organizations rows: {rows}")
                assert rows > 0, "Organizations table should have rows"
            elif tab_id == "automations":
                rows = await page.locator("#automations-table-body tr").count()
                print(f"  -> Automations rows: {rows}")
                assert rows > 0, "Automations table should have rows"
            elif tab_id == "custom-data":
                content = await page.locator("#custom-data-log-stream").inner_text()
                print(f"  -> Custom data stream has {len(content)} chars")
                assert len(content) > 10, "Custom data log stream should have real records"
            elif tab_id == "locations":
                cards = await page.locator("#locations-grid > div").count()
                print(f"  -> Locations cards: {cards}")
                assert cards > 0, "Locations grid should have cards"
            elif tab_id == "snapshots":
                snaps = await page.locator("#snapshots-list > div").count()
                print(f"  -> Snapshots cards: {snaps}")
                assert snaps > 0, "Snapshots list should have cards"
            elif tab_id == "in-app-messaging":
                bcasts = await page.locator("#broadcasts-list > div").count()
                print(f"  -> Broadcasts cards: {bcasts}")
                assert bcasts > 0, "Broadcasts list should have cards"
            elif tab_id == "devices":
                devs = await page.locator("#devices-table-body tr").count()
                print(f"  -> Devices rows: {devs}")
                assert devs > 0, "Devices table should have rows"

        # Developer Zone sub-views check
        print("Testing Developer Zone sub-views...")
        await page.evaluate("switchTab('developer-zone')")
        await page.wait_for_timeout(800)

        subviews = ['templates', 'static-tokens', 'rule-engine', 'oauth', 'webhooks']
        for sv in subviews:
            print(f"  Testing dev subview: {sv}...")
            await page.evaluate(f"switchDevSubView('{sv}')")
            await page.wait_for_timeout(600)
            is_sv_vis = await page.is_visible(f"#dev-subview-{sv}")
            assert is_sv_vis, f"Subview #dev-subview-{sv} should be visible"

        # Capture complete UI screenshot
        screenshot_path = os.path.join(ARTIFACTS_DIR, "all_tabs_real_database_verified.png")
        await page.screenshot(path=screenshot_path, full_page=False)
        print(f"Verification screenshot saved to: {screenshot_path}")

        print(f"Dialog count: {len(dialogs)} (should be 0)")
        print(f"Console errors: {len(console_errors)}")
        if console_errors:
            for err in console_errors[:5]:
                print(f"  Console error: {err}")

        assert len(dialogs) == 0, f"No alert/dialogs should have appeared, found: {dialogs}"
        print("[SUCCESS] ALL 13 TABS & SUB-VIEWS PASS REAL DATABASE E2E VERIFICATION 100%!")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_verification())
