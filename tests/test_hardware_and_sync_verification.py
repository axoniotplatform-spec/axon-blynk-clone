import asyncio
import socket
import struct
import json
import urllib.request
import sys
import os
from pathlib import Path

# Ensure axon_iot root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.database import SessionLocal
from backend.models.entities import Device, Datastream

BASE_URL = "http://127.0.0.1:8000"
TCP_HOST = "127.0.0.1"
TCP_PORT = 8080

def test_http_routes():
    print("\n--- 1. Testing Web Console & Mobile App HTTP Routes ---")
    
    # 1. Web Console index
    req = urllib.request.Request(f"{BASE_URL}/")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        html = resp.read().decode('utf-8')
        assert "Axon IoT" in html or "Blynk" in html
        print("[PASS] Web Console HTTP 200 OK (index.html loaded)")

    # 2. Mobile App UI
    req_app = urllib.request.Request(f"{BASE_URL}/app")
    with urllib.request.urlopen(req_app) as resp:
        assert resp.status == 200
        app_html = resp.read().decode('utf-8')
        assert "device-widgets-grid" in app_html and "Blynk" in app_html
        print("[PASS] Mobile App HTTP 200 OK (/app loaded)")

    # 3. Users API
    req_users = urllib.request.Request(f"{BASE_URL}/api/v1/users")
    with urllib.request.urlopen(req_users) as resp:
        assert resp.status == 200
        users = json.loads(resp.read().decode('utf-8'))
        assert isinstance(users, list)
        print(f"[PASS] Users API OK. Found {len(users)} users: {[u['email'] for u in users]}")

def test_embedded_hardware_connection():
    print("\n--- 2. Testing Embedded Hardware TCP Protocol (ESP32/Arduino on Port 8080) ---")
    
    # Fetch token directly from DB
    db = SessionLocal()
    dev = db.query(Device).first()
    token = dev.auth_token if dev else "yhdHK6Vuj2F6X7CUnX-QQIpuEl9Yy_dk"
    db.close()
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((TCP_HOST, TCP_PORT))
    print(f"[Connected] Embedded hardware socket open to {TCP_HOST}:{TCP_PORT}")

    # Blynk packet constants
    BLYNK_CMD_RESPONSE = 0x00
    BLYNK_CMD_LOGIN = 0x02
    BLYNK_CMD_PING = 0x06
    BLYNK_CMD_HARDWARE = 0x14
    BLYNK_STATUS_SUCCESS = 200

    # Step A: ESP32 sends BLYNK_CMD_LOGIN with Auth Token
    token_bytes = token.encode('ascii')
    msg_id = 1
    login_frame = struct.pack(">BHH", BLYNK_CMD_LOGIN, msg_id, len(token_bytes)) + token_bytes
    s.sendall(login_frame)
    print(f"[ESP32 -> Gateway] Sent BLYNK_CMD_LOGIN with token: {token}")

    # Read 5-byte response header
    resp_header = s.recv(5)
    resp_cmd, resp_id, resp_status = struct.unpack(">BHH", resp_header)
    print(f"[Gateway -> ESP32] Received Response: cmd={resp_cmd}, msg_id={resp_id}, status={resp_status}")
    assert resp_cmd == BLYNK_CMD_RESPONSE
    assert resp_status == BLYNK_STATUS_SUCCESS
    print("[PASS] ESP32 Authentication SUCCESS (200 OK)!")

    # Step B: Arduino / ESP32 sends virtual telemetry write: Blynk.virtualWrite(V2, 33.5)
    # Binary format: vw\0 2\0 33.5
    body = b"vw\0002\00033.5"
    msg_id += 1
    hw_frame = struct.pack(">BHH", BLYNK_CMD_HARDWARE, msg_id, len(body)) + body
    s.sendall(hw_frame)
    print(f"[ESP32 -> Gateway] Sent Blynk.virtualWrite(V2, 33.5) [Temperature Telemetry]")

    # Step C: Send Heartbeat / Ping
    msg_id += 1
    ping_frame = struct.pack(">BHH", BLYNK_CMD_PING, msg_id, 0)
    s.sendall(ping_frame)
    ping_resp = s.recv(5)
    p_cmd, p_id, p_status = struct.unpack(">BHH", ping_resp)
    assert p_cmd == BLYNK_CMD_RESPONSE
    assert p_status == BLYNK_STATUS_SUCCESS
    print(f"[PASS] Hardware Ping/Heartbeat ACK OK (status={p_status})")

    s.close()
    print("[PASS] Embedded hardware TCP test completed cleanly.")

def test_account_creation_sync():
    print("\n--- 3. Testing Unified Account Creation & Sync (Web <-> Mobile App) ---")
    
    # Register new account via mobile / web endpoint
    test_email = "embedded.dev@axon.io"
    payload = json.dumps({
        "name": "Alex Embedded Dev",
        "email": test_email,
        "password": "securepassword123",
        "role": "Admin"
    }).encode('utf-8')

    req = urllib.request.Request(
        f"{BASE_URL}/api/v1/auth/register",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print(f"[PASS] User registered successfully: {data['user']}")
            assert data["user"]["email"] == test_email
    except urllib.error.HTTPError as e:
        if e.code == 400:
            print(f"[INFO] User {test_email} already exists, continuing verification.")
        else:
            raise

    # Verify user appears in unified users list queryable by both Web Console and App
    req_users = urllib.request.Request(f"{BASE_URL}/api/v1/users")
    with urllib.request.urlopen(req_users) as resp:
        users = json.loads(resp.read().decode('utf-8'))
        matching = [u for u in users if u["email"] == test_email]
        assert len(matching) > 0
        print(f"[PASS] Verified user '{test_email}' is present in cloud user directory!")

if __name__ == "__main__":
    test_http_routes()
    test_embedded_hardware_connection()
    test_account_creation_sync()
    print("\nALL BACKEND & EMBEDDED HARDWARE GATEWAY TESTS PASSED 100%!")
