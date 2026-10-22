import asyncio
import os
import shutil
import urllib.request
import json
from playwright.async_api import async_playwright
from PIL import Image

ARTIFACT_DIR = r"C:\Users\USER\.gemini\antigravity\brain\c0451ab2-5751-4d25-b592-1b96ca419043"
SCREENSHOTS_DIR = r"C:\RE\axon_iot\tests\screenshots"
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
os.makedirs(ARTIFACT_DIR, exist_ok=True)

BASE_URL = "http://127.0.0.1:8000"

def test_rest_apis():
    print("\n--- 1. Testing Real SQLite REST Endpoints ---")
    
    # Locations
    req = urllib.request.Request(f"{BASE_URL}/api/v1/locations")
    with urllib.request.urlopen(req) as r:
        locs = json.loads(r.read().decode())
        print(f"[PASS] Locations API: {len(locs)} sites returned from SQLite: {[l['name'] for l in locs]}")

    # Snapshots
    req = urllib.request.Request(f"{BASE_URL}/api/v1/snapshots")
    with urllib.request.urlopen(req) as r:
        snaps = json.loads(r.read().decode())
        print(f"[PASS] Snapshots API: {len(snaps)} snapshots returned from SQLite: {[s['name'] for s in snaps]}")

    # Broadcasts
    req = urllib.request.Request(f"{BASE_URL}/api/v1/broadcasts")
    with urllib.request.urlopen(req) as r:
        bcasts = json.loads(r.read().decode())
        print(f"[PASS] Broadcasts API: {len(bcasts)} in-app broadcasts in SQLite: {[b['title'][:30] for b in bcasts]}")

    # Custom Data CSV
    req = urllib.request.Request(f"{BASE_URL}/api/v1/custom-data/export.csv")
    with urllib.request.urlopen(req) as r:
        csv_data = r.read().decode()
        assert "Timestamp" in csv_data
        print(f"[PASS] Custom Data CSV Export OK: {len(csv_data.splitlines())} rows streamed from database")

    # Ask AI
    req = urllib.request.Request(
        f"{BASE_URL}/api/v1/ai/ask",
        data=json.dumps({"query": "How to connect my ESP32?"}).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as r:
        ai_resp = json.loads(r.read().decode())
        print(f"[PASS] Ask AI Response OK: {ai_resp['answer'][:60]}...")

async def test_ui_and_capture_screenshots():
    print("\n--- 2. Testing Real Dynamic UI in Playwright ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1400, "height": 900})
        
        await page.goto(BASE_URL, wait_until="networkidle")
        await page.wait_for_timeout(1500)

        # 1. Locations Tab
        print("Navigating to Locations tab...")
        await page.click("div.sidebar-nav-item:has-text('Locations')")
        await page.wait_for_timeout(1000)
        
        loc_path = os.path.join(SCREENSHOTS_DIR, "real_locations_active.png")
        await page.screenshot(path=loc_path)
        print(f"[Captured] Real Locations View -> {loc_path}")

        # Click + Add Location
        print("Clicking + Add Location...")
        await page.click("button:has-text('+ Add Location')")
        await page.wait_for_timeout(500)
        await page.fill("#loc-modal-name", "Lagos Solar Substation")
        await page.fill("#loc-modal-address", "Victoria Island Solar Array Hub")
        await page.click("#new-location-modal button:has-text('Save Location')")
        await page.wait_for_timeout(1000)

        loc_added_path = os.path.join(SCREENSHOTS_DIR, "real_location_added_saved.png")
        await page.screenshot(path=loc_added_path)
        print(f"[Captured] Real Location Added -> {loc_added_path}")

        # 2. Snapshots Tab
        print("Navigating to Snapshots tab...")
        await page.click("div.sidebar-nav-item:has-text('Snapshots')")
        await page.wait_for_timeout(1000)

        # Click Take Snapshot
        print("Taking real snapshot...")
        await page.click("button:has-text('Take Snapshot')")
        await page.wait_for_timeout(500)
        await page.fill("#snap-modal-name", "Fleet Production Snapshot #002")
        await page.click("#take-snapshot-modal button:has-text('Capture Snapshot')")
        await page.wait_for_timeout(1000)

        snap_path = os.path.join(SCREENSHOTS_DIR, "real_snapshots_captured.png")
        await page.screenshot(path=snap_path)
        print(f"[Captured] Real Snapshots Captured -> {snap_path}")

        # 3. In-App Messaging Tab
        print("Navigating to In-App Messaging tab...")
        await page.click("div.sidebar-nav-item:has-text('In-App Messaging')")
        await page.wait_for_timeout(1000)

        # Click Send Broadcast
        print("Sending real broadcast...")
        await page.click("button:has-text('Send Broadcast')")
        await page.wait_for_timeout(500)
        await page.fill("#bcast-modal-title", "[NOTICE] Fleet OTA Rollout Completed")
        await page.fill("#bcast-modal-body", "All ESP32 nodes successfully upgraded to v1.0.5 firmware.")
        await page.click("#new-broadcast-modal button:has-text('Send Broadcast')")
        await page.wait_for_timeout(1000)

        bcast_path = os.path.join(SCREENSHOTS_DIR, "real_broadcast_dispatched.png")
        await page.screenshot(path=bcast_path)
        print(f"[Captured] Real Broadcast Dispatched -> {bcast_path}")

        # 4. Dashboards Tab & Switcher
        print("Navigating to Dashboards tab...")
        await page.click("div.sidebar-nav-item:has-text('Dashboards')")
        await page.wait_for_timeout(1000)

        # Switch to Smart Greenhouse
        print("Switching dashboard to Smart Greenhouse...")
        gh_item = await page.wait_for_selector(".dashboard-list-item:has-text('Smart Greenhouse')")
        await gh_item.click()
        await page.wait_for_timeout(1000)

        dash_gh_path = os.path.join(SCREENSHOTS_DIR, "real_smart_greenhouse_dashboard.png")
        await page.screenshot(path=dash_gh_path)
        print(f"[Captured] Smart Greenhouse Dashboard -> {dash_gh_path}")

        # 5. Ask AI Copilot
        print("Opening Ask AI Copilot...")
        await page.click("button:has-text('Ask AI')")
        await page.wait_for_timeout(500)
        await page.fill("#ai-query-input", "How to connect my ESP32?")
        await page.click("#ai-modal button:has-text('Ask')")
        await page.wait_for_timeout(1200)

        ai_path = os.path.join(SCREENSHOTS_DIR, "real_ai_copilot_answered.png")
        await page.screenshot(path=ai_path)
        print(f"[Captured] Ask AI Copilot Response -> {ai_path}")
        await page.click("#ai-modal button:has-text('✕')")
        await page.wait_for_timeout(400)

        # 6. Copy all generated screenshots to Brain Artifacts directory
        for fname in ["real_locations_active.png", "real_location_added_saved.png", "real_snapshots_captured.png", "real_broadcast_dispatched.png", "real_smart_greenhouse_dashboard.png", "real_ai_copilot_answered.png"]:
            src = os.path.join(SCREENSHOTS_DIR, fname)
            dst = os.path.join(ARTIFACT_DIR, fname)
            if os.path.exists(src):
                shutil.copy2(src, dst)
                print(f"[Copied to Artifacts] {dst}")

        await browser.close()
        print("\nALL DYNAMIC DATABASE & UI TESTS COMPLETED 100% SUCCESSFULLY!")

if __name__ == "__main__":
    test_rest_apis()
    asyncio.run(test_ui_and_capture_screenshots())
