import os
import time
from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = r"C:\Users\USER\.gemini\antigravity\brain\c0451ab2-5751-4d25-b592-1b96ca419043"

def run_suite():
    print("=== STARTING FULL SUITE AUTOMATION TEST ===")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto("http://127.0.0.1:8000/")
        page.wait_for_timeout(1000)

        # 1. Developer Zone - Template Details & Subtabs
        print("1. Testing Developer Zone...")
        page.locator(".sidebar-nav-item:has-text('Developer Zone')").click()
        page.wait_for_timeout(800)
        
        # Click on BLINKING LED template card
        page.locator(".template-card:has-text('BLINKING LED')").click()
        page.wait_for_timeout(800)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "step1_template_home.png"))
        print(" -> Template Home subtab captured.")

        # Subtab: Datastreams
        page.locator(".subtab-item:has-text('Datastreams')").click()
        page.wait_for_timeout(1000)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "step2_template_datastreams.png"))
        print(" -> Template Datastreams subtab captured.")

        # Modal: New Datastream
        page.locator("button:has-text('+ New Datastream')").click()
        page.wait_for_timeout(600)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "step3_modal_new_datastream.png"))
        print(" -> New Datastream modal captured.")

        # Submit New Datastream (V9)
        page.locator("button:has-text('Create Datastream')").click()
        page.wait_for_timeout(1200)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "step4_datastream_v9_added.png"))
        print(" -> Datastream V9 added to table captured.")

        # Subtab: Web Dashboard
        page.locator(".subtab-item:has-text('Web Dashboard')").click()
        page.wait_for_timeout(800)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "step5_template_web_dashboard.png"))
        print(" -> Template Web Dashboard & Widget Box captured.")

        # Subtab: Metadata
        page.locator(".subtab-item:has-text('Metadata')").click()
        page.wait_for_timeout(600)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "step6_template_metadata.png"))
        print(" -> Template Metadata subtab captured.")

        # 2. Automations Tab
        print("2. Testing Automations Tab...")
        page.locator(".sidebar-nav-item:has-text('Automations')").click()
        page.wait_for_timeout(800)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "step7_automations_table.png"))
        print(" -> Automations table captured.")

        # Create Automation Modal
        page.locator("button:has-text('+ Create Automation')").click()
        page.wait_for_timeout(600)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "step8_modal_new_automation.png"))
        print(" -> New Automation modal captured.")

        page.locator("button:has-text('Save Automation')").click()
        page.wait_for_timeout(800)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "step9_automation_saved.png"))
        print(" -> Automation saved captured.")

        print("=== ALL SUITE TESTS COMPLETED SUCCESSFULLY ===")
        browser.close()

if __name__ == "__main__":
    run_suite()
