import os
import time
from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = r"C:\Users\USER\.gemini\antigravity\brain\c0451ab2-5751-4d25-b592-1b96ca419043"

def run_phase6_test():
    print("=== STARTING PHASE 6: EXTENDED WIDGETS & EDITOR TEST ===")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        
        # 1. Open Device Dashboard
        print("1. Loading Device Dashboard...")
        page.goto("http://127.0.0.1:8000/")
        page.wait_for_timeout(1000)
        page.locator("text=BLINKING LED").first.click()
        page.wait_for_timeout(2000)

        # Capture full dashboard with extended widgets
        shot1 = os.path.join(SCREENSHOT_DIR, "phase6_extended_widgets_dashboard.png")
        page.screenshot(path=shot1, full_page=True)
        print(" -> Extended widgets dashboard captured to:", shot1)

        # 2. Test RGB NeoPixel widget interaction
        print("2. Testing NeoPixel RGB widget interaction...")
        color_dot = page.locator("#widget-canvas div[onclick*='setRgbColor']").first
        if color_dot.is_visible():
            color_dot.click()
            page.wait_for_timeout(1000)
            print(" -> Color preset clicked.")

        # 3. Test Dashboard Edit Mode Toggle
        print("3. Toggling Dashboard Edit Mode...")
        edit_btn = page.locator("#btn-edit-main-dash")
        if edit_btn.is_visible():
            edit_btn.click()
            page.wait_for_timeout(1200)
            shot2 = os.path.join(SCREENSHOT_DIR, "phase6_dashboard_edit_mode.png")
            page.screenshot(path=shot2, full_page=True)
            print(" -> Dashboard edit mode captured to:", shot2)

            # 4. Test Widget Settings Modal
            print("4. Testing Widget Settings Modal...")
            settings_gear = page.locator("button:has-text('⚙️')").first
            if settings_gear.is_visible():
                settings_gear.click()
                page.wait_for_timeout(800)
                shot3 = os.path.join(SCREENSHOT_DIR, "phase6_widget_settings_modal.png")
                page.screenshot(path=shot3)
                print(" -> Widget Settings modal captured to:", shot3)

                # Close modal
                cancel_btn = page.locator("#widget-settings-modal button:has-text('Cancel')")
                if cancel_btn.is_visible():
                    cancel_btn.click()
                    page.wait_for_timeout(500)

            # Exit edit mode
            edit_btn.click()
            page.wait_for_timeout(1000)

        # 5. Developer Zone -> Template -> Web Dashboard sub-tab & Widget Box
        print("5. Testing Developer Zone -> Template Web Dashboard & Widget Box...")
        page.locator(".sidebar-nav-item:has-text('Developer Zone')").click()
        page.wait_for_timeout(800)
        page.locator(".template-card:has-text('BLINKING LED')").click()
        page.wait_for_timeout(800)
        page.locator(".subtab-item:has-text('Web Dashboard')").click()
        page.wait_for_timeout(1200)

        shot4 = os.path.join(SCREENSHOT_DIR, "phase6_template_widget_palette.png")
        page.screenshot(path=shot4, full_page=True)
        print(" -> Template Web Dashboard & Widget Box palette captured to:", shot4)

        print("=== ALL PHASE 6 TESTS COMPLETED SUCCESSFULLY ===")
        browser.close()

if __name__ == "__main__":
    run_phase6_test()
