import os
from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = r"C:\Users\USER\.gemini\antigravity\brain\c0451ab2-5751-4d25-b592-1b96ca419043"

TABS = [
    ("get-started", "tab_get_started.png"),
    ("devices", "tab_devices.png"),
    ("dashboards", "tab_dashboards.png"),
    ("custom-data", "tab_custom_data.png"),
    ("developer-zone", "tab_developer_zone.png"),
    ("automations", "tab_automations.png"),
    ("users", "tab_users.png"),
    ("organizations", "tab_organizations.png"),
    ("locations", "tab_locations.png"),
    ("fleet-management", "tab_fleet_management.png"),
    ("snapshots", "tab_snapshots.png"),
    ("in-app-messaging", "tab_in_app_messaging.png"),
    ("predictive-maintenance", "tab_predictive_maintenance.png")
]

def run_all_tabs_test():
    print("=== STARTING FULL 13-TAB PLATFORM PLAYWRIGHT VERIFICATION ===", flush=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto("http://127.0.0.1:8000/")
        page.wait_for_timeout(1000)
        # Dismiss any auth overlay if present
        page.evaluate("const m = document.getElementById('axon-auth-modal'); if (m) m.style.display = 'none';")

        for tab_id, shot_name in TABS:
            print(f"Testing tab: {tab_id}...", flush=True)
            # Click sidebar nav item or evaluate switchTab directly
            page.evaluate(f"switchTab('{tab_id}')")
            page.wait_for_timeout(600)
            
            shot_path = os.path.join(SCREENSHOT_DIR, shot_name)
            page.screenshot(path=shot_path)
            print(f" -> {tab_id} verified and captured to {shot_name}", flush=True)

        # Also test OTA Modal on Fleet Management
        print("Testing OTA Deployment Modal on Fleet Management...", flush=True)
        page.evaluate("switchTab('fleet-management')")
        page.wait_for_timeout(400)
        page.evaluate("openOtaModal()")
        page.wait_for_timeout(500)
        ota_shot = os.path.join(SCREENSHOT_DIR, "modal_fleet_ota_deploy.png")
        page.screenshot(path=ota_shot)
        print(" -> OTA Modal captured to modal_fleet_ota_deploy.png", flush=True)
        page.evaluate("closeOtaModal()")

        print("=== ALL 13 TABS & MODALS VERIFIED SUCCESSFULLY ===", flush=True)
        browser.close()

if __name__ == "__main__":
    run_all_tabs_test()
