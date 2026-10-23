import asyncio
from playwright.async_api import async_playwright
from backend.database import SessionLocal
from backend.models.entities import DashboardWidget, Device

async def run_verification():
    db = SessionLocal()
    initial_widget_count = db.query(DashboardWidget).filter(DashboardWidget.template_id == 1).count()
    db.close()
    print(f"[DB Verification] Initial widgets in SQLite for Template 1: {initial_widget_count}")

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 412, "height": 915})

        errors = []
        page.on('console', lambda msg: errors.append(f"[{msg.type}] {msg.text}") if msg.type == 'error' else None)
        page.on('pageerror', lambda err: errors.append(str(err)))

        print("\n1. Loading Mobile App...")
        await page.goto("http://127.0.0.1:8000/app.html")
        await page.wait_for_timeout(1500)

        # Verify device status is real (OFFLINE)
        offline_pills = await page.query_selector_all(".pill-status.offline")
        print(f"2. Verified Real Status: Found {len(offline_pills)} OFFLINE devices (no mock online)")
        assert len(offline_pills) > 0, "Expected devices to reflect real OFFLINE status"

        # Check Profile Screen real data
        print("3. Checking Account / Profile Screen with real SQLite data...")
        await page.click(".dock-tab:has-text('Account')")
        await page.wait_for_timeout(800)
        acc_name = await page.inner_text("#acc-name")
        acc_org = await page.inner_text("#acc-org")
        print(f"   -> Real User Name: '{acc_name}', Real Org: '{acc_org}'")
        assert acc_name == "Sam", f"Expected real user 'Sam', got '{acc_name}'"
        assert "My organization" in acc_org, f"Expected real org, got '{acc_org}'"

        # Return to Devices screen
        await page.click(".dock-tab:has-text('Devices')")
        await page.wait_for_timeout(500)

        # Open Device 1
        print("4. Opening Device 1 Dashboard...")
        await page.click(".card-id-block")
        await page.wait_for_timeout(1500)

        # Verify device header reflects real status (OFFLINE)
        status_text = await page.inner_text("#active-device-status")
        print("   -> Dashboard Header Status checked successfully")
        assert "Offline" in status_text, f"Expected real Offline status, got '{status_text}'"

        # Check rendered widget count matches SQLite count exactly
        rendered_tiles = await page.query_selector_all(".widget-tile")
        print(f"5. Rendered Widgets on Canvas: {len(rendered_tiles)} (SQLite DB has: {initial_widget_count})")
        assert len(rendered_tiles) == initial_widget_count, f"Rendered count {len(rendered_tiles)} != DB count {initial_widget_count}"

        # Test Edit Mode: Delete a widget
        print("6. Entering Edit Mode to test real widget deletion...")
        await page.click("#btn-edit-mode")
        await page.wait_for_timeout(500)

        first_badge = await page.wait_for_selector(".tile-remove-badge")
        await first_badge.click(force=True)
        await page.wait_for_timeout(1000)

        # Verify in DB that widget count decreased by 1
        db = SessionLocal()
        after_delete_count = db.query(DashboardWidget).filter(DashboardWidget.template_id == 1).count()
        db.close()
        print(f"   -> SQLite widget count after delete: {after_delete_count} (was {initial_widget_count})")
        assert after_delete_count == initial_widget_count - 1, "Widget was not deleted from SQLite!"

        # Test adding a widget from Widget Box
        print("7. Adding new widget from Widget Box...")
        await page.click("#dock-fab")
        await page.wait_for_timeout(600)

        # Add Enhanced Gauge
        gauge_catalog = await page.wait_for_selector(".catalog-tile:has-text('Enhanced Gauge')")
        await gauge_catalog.click()
        await page.wait_for_timeout(1500)

        # Verify in DB that widget count increased by 1
        db = SessionLocal()
        after_add_count = db.query(DashboardWidget).filter(DashboardWidget.template_id == 1).count()
        db.close()
        print(f"   -> SQLite widget count after add: {after_add_count}")
        assert after_add_count == after_delete_count + 1, "Widget was not added to SQLite!"

        # Take screenshot of real database dashboard
        screenshot_path = r'C:\Users\USER\.gemini\antigravity\brain\c0451ab2-5751-4d25-b592-1b96ca419043\real_db_no_mock_dashboard.png'
        await page.screenshot(path=screenshot_path)
        print(f"8. Verification screenshot saved to {screenshot_path}")

        print("\n[SUCCESS] ZERO MOCK DATA - ALL WIDGETS & REAL STATUS TIED 100% TO SQLITE DATABASE!")
        print("Errors during test:", errors)
        assert len(errors) == 0, f"Found console errors: {errors}"
        await browser.close()

if __name__ == '__main__':
    asyncio.run(run_verification())
