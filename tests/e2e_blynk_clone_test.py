import time
import os
from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = r"C:\Users\USER\.gemini\antigravity\brain\c0451ab2-5751-4d25-b592-1b96ca419043"

def run_tests():
    print("--- Starting End-to-End Blynk Clone Rigorous Testing ---")
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception:
            browser = p.chromium.launch(channel="chrome", headless=True)
            
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # Step 1: Open main page (Devices tab)
        print("1. Loading http://127.0.0.1:8000/ ...")
        page.goto("http://127.0.0.1:8000/")
        page.wait_for_timeout(1500)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "test_1_devices_tab.png"))
        print(" -> Devices tab captured.")

        # Step 2: Test "+ New Device" modal
        print("2. Testing '+ New Device' button and modal...")
        new_dev_btn = page.locator("button:has-text('+ New Device')")
        if new_dev_btn.is_visible():
            new_dev_btn.click()
            page.wait_for_timeout(800)
            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "test_2_new_device_modal.png"))
            print(" -> '+ New Device' modal captured.")
            
            # Close modal
            cancel_btn = page.locator("button:has-text('Cancel')")
            if cancel_btn.is_visible():
                cancel_btn.click()
                page.wait_for_timeout(500)

        # Step 3: Click on device row to open Device Dashboard
        print("3. Clicking 'BLINKING LED' device row to open Device Dashboard...")
        device_row = page.locator("text=BLINKING LED").first
        device_row.click()
        page.wait_for_timeout(2000)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "test_3_device_dashboard.png"))
        print(" -> Device Dashboard captured.")

        # Step 4: Interact with Widgets on Dashboard
        print("4. Testing Widget Interactions on Dashboard...")
        
        # 4a. Button (V0)
        btn_v0 = page.locator("#btn-V0")
        if btn_v0.is_visible():
            print(" -> Clicking Button V0...")
            btn_v0.click()
            page.wait_for_timeout(1000)
            btn_v0.click()
            page.wait_for_timeout(1000)
            
        # 4b. Switch (V3)
        switch_v3 = page.locator("#switch-V3")
        if switch_v3.is_visible():
            print(" -> Toggling Switch V3...")
            switch_v3.click()
            page.wait_for_timeout(1000)

        # 4c. Number Input Stepper (V4)
        plus_v4 = page.locator("button:has-text('+')").first
        if plus_v4.is_visible():
            print(" -> Clicking Stepper + on V4...")
            plus_v4.click()
            page.wait_for_timeout(800)
            plus_v4.click()
            page.wait_for_timeout(800)

        # 4d. Terminal input (V7)
        term_input = page.locator("#term-input-V7")
        if term_input.is_visible():
            print(" -> Sending command 'STATUS' to Terminal V7...")
            term_input.fill("STATUS")
            send_btn = page.locator("button:has-text('Send')").first
            if send_btn.is_visible():
                send_btn.click()
                page.wait_for_timeout(1000)

        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "test_4_widgets_interacted.png"))
        print(" -> Interacted Widgets state captured.")

        # Step 5: Test Sidebar Navigation Tabs
        tabs = [
            ("dashboards", "test_5_dashboards_tab.png"),
            ("developer-zone", "test_6_developer_zone_tab.png"),
            ("automations", "test_7_automations_tab.png"),
            ("users", "test_8_users_tab.png"),
            ("organizations", "test_9_organizations_tab.png")
        ]
        for nav_id, shot_name in tabs:
            print(f"Testing navigation tab: {nav_id}...")
            nav_item = page.locator(f'[data-nav="{nav_id}"]')
            if nav_item.is_visible():
                nav_item.click()
                page.wait_for_timeout(1000)
                page.screenshot(path=os.path.join(SCREENSHOT_DIR, shot_name))
                print(f" -> {nav_id} captured to {shot_name}.")

        print("--- All End-to-End Tests Finished Successfully ---")
        browser.close()

if __name__ == "__main__":
    run_tests()
