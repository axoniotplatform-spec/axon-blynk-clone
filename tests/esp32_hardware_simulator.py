import socket
import struct
import time
import os
import urllib.request
import json
from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = r"C:\Users\USER\.gemini\antigravity\brain\c0451ab2-5751-4d25-b592-1b96ca419043"
AUTH_TOKEN = "yhdHK6Vuj2F6X7CUnX-QQIpuEl9Yy_dk"

# Protocol Constants
CMD_RESPONSE = 0x00
CMD_LOGIN = 0x02
CMD_PING = 0x06
CMD_HARDWARE = 0x14

def run_hardware_simulation():
    print("=== STARTING PHASE 7: BLYNK HARDWARE PROTOCOL & ESP32 SIMULATION ===")
    
    # Connect TCP socket to Blynk Gateway on port 8080
    print("1. Connecting TCP socket to 127.0.0.1:8080 (Blynk Protocol Gateway)...")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5.0)
    s.connect(("127.0.0.1", 8080))
    print(" -> TCP connected.")

    # 1. Login Command
    print("2. Sending Blynk LOGIN frame with Auth Token...")
    token_bytes = AUTH_TOKEN.encode('ascii')
    login_frame = struct.pack(">BHH", CMD_LOGIN, 1, len(token_bytes)) + token_bytes
    s.sendall(login_frame)

    # Read 5-byte response header
    resp_hdr = s.recv(5)
    cmd, msg_id, status = struct.unpack(">BHH", resp_hdr)
    print(f" -> Response received: cmd={cmd}, msg_id={msg_id}, status={status}")
    assert cmd == CMD_RESPONSE and status == 200, f"Login failed! status={status}"
    print(" -> ESP32 Authenticated successfully with Blynk Core!")

    # 2. Ping Command
    print("3. Sending Blynk PING frame...")
    ping_frame = struct.pack(">BHH", CMD_PING, 2, 0)
    s.sendall(ping_frame)
    resp_hdr = s.recv(5)
    cmd, msg_id, status = struct.unpack(">BHH", resp_hdr)
    assert cmd == CMD_RESPONSE and status == 200, f"Ping failed! status={status}"
    print(" -> Ping verified: status=200 OK.")

    # 3. Virtual Write: Send Temperature = 36.8 C on V2 (vw\0 2\0 36.8)
    print("4. Sending Hardware Telemetry: Blynk.virtualWrite(V2, 36.8)...")
    payload = b"vw\0002\00036.8"
    hw_frame = struct.pack(">BHH", CMD_HARDWARE, 3, len(payload)) + payload
    s.sendall(hw_frame)
    print(" -> Frame dispatched to gateway.")

    time.sleep(1.0)

    # 4. Verify value updated in platform via REST API
    v2_val = urllib.request.urlopen(f"http://127.0.0.1:8000/external/api/get?token={AUTH_TOKEN}&pin=V2").read().decode()
    print(f" -> Verified V2 value in platform: {v2_val} °C")
    assert v2_val == "36.8", f"Expected 36.8, got {v2_val}"

    # 5. Verify Automations triggered Fan Relay V3 = 1
    v3_val = urllib.request.urlopen(f"http://127.0.0.1:8000/external/api/get?token={AUTH_TOKEN}&pin=V3").read().decode()
    print(f" -> Verified V3 (Fan Relay) state: {v3_val}")
    assert v3_val == "1", f"Expected 1, got {v3_val}"

    # 6. Capture live console screenshot using Playwright
    print("5. Capturing live browser dashboard with hardware active...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        page.goto("http://127.0.0.1:8000/")
        page.wait_for_timeout(1000)
        page.locator("text=BLINKING LED").first.click()
        page.wait_for_timeout(2000)

        shot = os.path.join(SCREENSHOT_DIR, "phase7_hardware_tcp_telemetry_live.png")
        page.screenshot(path=shot, full_page=True)
        print(" -> Live dashboard screenshot captured to:", shot)
        browser.close()

    s.close()
    print("=== PHASE 7: HARDWARE PROTOCOL SIMULATION COMPLETED WITH 100% SUCCESS ===")

if __name__ == "__main__":
    run_hardware_simulation()
