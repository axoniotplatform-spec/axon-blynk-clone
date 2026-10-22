import asyncio
import socket
import struct
import json
import urllib.request
from playwright.async_api import async_playwright

SCREENSHOT_DIR = r"C:\Users\USER\.gemini\antigravity\brain\c0451ab2-5751-4d25-b592-1b96ca419043"

def send_blynk_tcp_telemetry(auth_token: str, pin: str, value: str):
    """Sends raw 5-byte Blynk binary frame over TCP port 8080"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("127.0.0.1", 8080))

    # 1. Login (cmd 0x02)
    token_bytes = auth_token.encode('ascii')
    login_hdr = struct.pack(">BHH", 2, 1, len(token_bytes))
    s.sendall(login_hdr + token_bytes)
    resp = s.recv(5)
    print(f"[Blynk TCP] Login response: {resp.hex()}")

    # 2. Hardware virtual write (cmd 0x14)
    # Payload: vw\0<pin>\0<val>
    pin_num = pin.replace("V", "")
    payload = f"vw\0{pin_num}\0{value}".encode('utf-8')
    hw_hdr = struct.pack(">BHH", 20, 2, len(payload))
    s.sendall(hw_hdr + payload)
    print(f"[Blynk TCP] Sent virtualWrite({pin}, {value})")

    # 3. Ping (cmd 0x06)
    ping_hdr = struct.pack(">BHH", 6, 3, 0)
    s.sendall(ping_hdr)
    s.close()

def send_blynk_http_telemetry(auth_token: str, pin: str, value: str):
    """Sends telemetry via Blynk External HTTP API /external/api/update"""
    url = f"http://127.0.0.1:8000/external/api/update?token={auth_token}&{pin}={value}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as resp:
        result = resp.read().decode()
        print(f"[Blynk HTTP] /external/api/update -> {result}")

async def run_fleet_multidevice_test():
    print("=== STARTING FLEET MULTI-DEVICE E2E TEST ===")

    # 1. Send live telemetry to Device 1 (ESP32 via TCP port 8080)
    send_blynk_tcp_telemetry("yhdHK6Vuj2F6X7CUnX-QQIpuEl9Yy_dk", "V2", "29.8")

    # 2. Send live telemetry to Device 2 (ESP8266 via HTTP API)
    send_blynk_http_telemetry("wZ3DBgWkDZ4aO9bwHvccU0rR0MUuD4xq", "V2", "31.5")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        # Step 1: Open Blynk Console
        print("Opening Blynk.Console UI...")
        await page.goto("http://127.0.0.1:8000/")
        await page.wait_for_selector("#devices-table-body")
        await page.wait_for_timeout(1000)

        # Capture Devices Table with multiple devices
        dev_rows = await page.locator("#devices-table-body tr").count()
        print(f"Initial devices rendered in table: {dev_rows}")
        await page.screenshot(path=f"{SCREENSHOT_DIR}\\fleet_step1_devices_table.png")

        # Step 2: Open "+ New Device" Modal and provision Node 3
        print("Opening '+ New Device' modal...")
        await page.click("button:has-text('New Device')")
        await page.wait_for_selector("#new-device-modal.open")
        await page.fill("#modal-device-name", "Solar Gateway - ESP32")
        await page.screenshot(path=f"{SCREENSHOT_DIR}\\fleet_step2_new_device_modal.png")

        # Confirm creation
        print("Confirming device provisioning...")
        await page.click("button:has-text('Create Device')")
        await page.wait_for_timeout(1200)

        # Check updated count
        dev_rows_after = await page.locator("#devices-table-body tr").count()
        print(f"Devices rendered after provisioning: {dev_rows_after}")
        await page.screenshot(path=f"{SCREENSHOT_DIR}\\fleet_step3_device_provisioned.png")

        # Step 3: Switch to Fleet Management Tab
        print("Navigating to Fleet Management Tab...")
        await page.click(".sidebar-nav-item:has-text('Fleet Management')")
        await page.wait_for_timeout(600)
        await page.screenshot(path=f"{SCREENSHOT_DIR}\\fleet_step4_fleet_management.png")

        # Step 4: Click OTA Deployment on Fleet Management
        print("Opening OTA Firmware Deployment Modal...")
        await page.click("button:has-text('🚀 Deploy OTA Firmware')")
        await page.wait_for_selector("#ota-modal.open")
        await page.wait_for_timeout(500)
        await page.screenshot(path=f"{SCREENSHOT_DIR}\\fleet_step5_ota_modal.png")

        # Close OTA modal before switching tabs
        print("Closing OTA modal...")
        await page.click("#ota-modal button:has-text('Cancel')")
        await page.wait_for_timeout(400)

        # Step 5: Switch to Live Dashboard
        print("Navigating to Dashboards Tab...")
        await page.click(".sidebar-nav-item:has-text('Dashboards')")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=f"{SCREENSHOT_DIR}\\fleet_step6_live_dashboard.png")

        await browser.close()
        print("=== FLEET MULTI-DEVICE E2E TEST COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    asyncio.run(run_fleet_multidevice_test())
