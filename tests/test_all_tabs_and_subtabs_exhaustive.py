import asyncio
from playwright.async_api import async_playwright

SCREENSHOT_DIR = r"C:\Users\USER\.gemini\antigravity\brain\c0451ab2-5751-4d25-b592-1b96ca419043"

async def test_exhaustive_tabs():
    print("=== STARTING EXHAUSTIVE TABS & SUBTABS TEST ===")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        await page.goto("http://127.0.0.1:8000/")
        await page.wait_for_timeout(1000)

        # 1. Get Started Tab
        print("[Tab 1/13] Testing Get Started...")
        await page.click(".sidebar-nav-item:has-text('Get Started')")
        await page.wait_for_timeout(400)
        await page.screenshot(path=f"{SCREENSHOT_DIR}\\subtab_get_started.png")

        # 2. Dashboards Tab
        print("[Tab 2/13] Testing Dashboards...")
        await page.click(".sidebar-nav-item:has-text('Dashboards')")
        await page.wait_for_timeout(400)
        # Click 6h interval pill
        await page.click(".segmented-pill:has-text('6h')")
        await page.wait_for_timeout(200)
        await page.screenshot(path=f"{SCREENSHOT_DIR}\\subtab_dashboards_split.png")

        # 3. Custom Data Tab
        print("[Tab 3/13] Testing Custom Data...")
        await page.click(".sidebar-nav-item:has-text('Custom Data')")
        await page.wait_for_timeout(400)
        await page.screenshot(path=f"{SCREENSHOT_DIR}\\subtab_custom_data.png")

        # 4. Developer Zone Tab & All Subtabs
        print("[Tab 4/13] Testing Developer Zone...")
        await page.click(".sidebar-nav-item:has-text('Developer Zone')")
        await page.wait_for_timeout(400)

        # Test secondary navigation items
        print("  Testing secondary nav items in Developer Zone...")
        await page.click(".dev-nav-item:has-text('Blueprints')")
        await page.wait_for_timeout(200)
        await page.click(".dev-nav-item:has-text('Blynk.Air')")
        await page.wait_for_timeout(200)
        await page.click(".dev-nav-item:has-text('Webhooks')")
        await page.wait_for_timeout(200)
        await page.click(".dev-nav-item:has-text('My Templates')")
        await page.wait_for_timeout(200)

        # Open Template Detail
        print("  Opening Template Detail (BLINKING LED)...")
        await page.click(".template-card:has-text('BLINKING LED')")
        await page.wait_for_timeout(400)

        # Test ALL 11 Template Subtabs!
        template_subtabs = [
            ("Home", "home"),
            ("Datastreams", "datastreams"),
            ("Dashboard", "dashboard"),
            ("Events & Notifications", "events"),
            ("Connection Lifecycle", "connection"),
            ("Data Converters", "converters"),
            ("Metadata", "metadata"),
            ("App Dashboard", "app-dashboard"),
            ("User Guides", "user-guides"),
            ("Automation Templates", "auto-templates"),
            ("Voice Assistants", "voice-assistants")
        ]
        for name, key in template_subtabs:
            print(f"    -> Subtab: {name}")
            await page.click(f"#template-detail-view .subtabs-bar .subtab-item:has-text('{name}')")
            await page.wait_for_timeout(200)
        
        await page.screenshot(path=f"{SCREENSHOT_DIR}\\subtab_template_voice_assistants.png")
        await page.click("#template-detail-view .subtabs-bar .subtab-item:has-text('Datastreams')")
        await page.wait_for_timeout(200)
        await page.screenshot(path=f"{SCREENSHOT_DIR}\\subtab_template_datastreams.png")

        # Close template detail
        await page.click("#template-detail-view button:has-text('Back to Templates')")
        await page.wait_for_timeout(300)

        # 5. Devices Tab & Device Subtabs
        print("[Tab 5/13] Testing Devices & Subtabs...")
        await page.click(".sidebar-nav-item:has-text('Devices')")
        await page.wait_for_timeout(400)
        await page.screenshot(path=f"{SCREENSHOT_DIR}\\subtab_devices_list.png")

        # Open Device Detail
        print("  Opening Device Detail subtabs view...")
        await page.click("#devices-table-body tr:first-child")
        await page.wait_for_timeout(400)

        device_subtabs = ["Device Dashboard", "Timeline", "Device Info", "Metadata"]
        for ds in device_subtabs:
            print(f"    -> Device Subtab: {ds}")
            await page.click(f"#device-subtabs-view .subtab-item:has-text('{ds}')")
            await page.wait_for_timeout(200)
            if ds == "Timeline":
                await page.screenshot(path=f"{SCREENSHOT_DIR}\\subtab_device_timeline.png")
            elif ds == "Device Info":
                await page.screenshot(path=f"{SCREENSHOT_DIR}\\subtab_device_info.png")

        # Back to device table
        await page.click("button:has-text('Back to Devices')")
        await page.wait_for_timeout(300)

        # 6. Automations Tab (5 Conditions)
        print("[Tab 6/13] Testing Automations...")
        await page.click(".sidebar-nav-item:has-text('Automations')")
        await page.wait_for_timeout(400)
        await page.screenshot(path=f"{SCREENSHOT_DIR}\\subtab_automations_5_conditions.png")

        # 7. Users Tab
        print("[Tab 7/13] Testing Users...")
        await page.click(".sidebar-nav-item:has-text('Users')")
        await page.wait_for_timeout(300)

        # 8. Organizations Tab
        print("[Tab 8/13] Testing Organizations...")
        await page.click(".sidebar-nav-item:has-text('Organizations')")
        await page.wait_for_timeout(300)

        # 9. Locations Tab
        print("[Tab 9/13] Testing Locations...")
        await page.click(".sidebar-nav-item:has-text('Locations')")
        await page.wait_for_timeout(300)

        # 10. Snapshots Tab
        print("[Tab 10/13] Testing Snapshots...")
        await page.click(".sidebar-nav-item:has-text('Snapshots')")
        await page.wait_for_timeout(300)

        # 11. Fleet Management Tab
        print("[Tab 11/13] Testing Fleet Management...")
        await page.click(".sidebar-nav-item:has-text('Fleet Management')")
        await page.wait_for_timeout(300)

        # 12. In-App Messaging Tab
        print("[Tab 12/13] Testing In-App Messaging...")
        await page.click(".sidebar-nav-item:has-text('In-App Messaging')")
        await page.wait_for_timeout(300)

        # 13. Predictive Maintenance Tab
        print("[Tab 13/13] Testing Predictive Maintenance...")
        await page.click(".sidebar-nav-item:has-text('Predictive Maintenance')")
        await page.wait_for_timeout(300)
        await page.screenshot(path=f"{SCREENSHOT_DIR}\\subtab_predictive_maint.png")

        # Collapse toggle test
        print("Testing Sidebar Collapse...")
        await page.click(".sidebar-collapse-btn")
        await page.wait_for_timeout(300)
        await page.click(".sidebar-collapse-btn")
        await page.wait_for_timeout(300)

        await browser.close()
        print("=== ALL 13 TABS AND ALL SUBTABS TESTED SUCCESSFULLY ===")

if __name__ == "__main__":
    asyncio.run(test_exhaustive_tabs())
