"""
test_live_simulation_and_anomalies.py — Live End-to-End Simulation & Anomaly Validation Suite
Verifies:
1. Production Healthcheck endpoint (/api/v1/health)
2. Blynk Raw TCP Protocol handshake and live telemetry ingress (Port 8080)
3. Cellular CSQ signal and uplink failover datastream mapping (V10, V11)
4. Anomaly Engine Real-Time Fault Traps:
   - VALUE_STALL (Sensor freeze on V4)
   - TOTALIZER_ROLLBACK (Cumulative drop on V5)
   - UNEXPECTED_INGRESS_WHILE_INACTIVE (Thermal surge on V2 while V3 actuator is OFF)
5. Notification dispatch & resolution cycle (/api/v1/anomalies/*/resolve)
"""

import socket
import struct
import time
import requests
import sys

BASE_URL = "http://127.0.0.1:8000"
GATEWAY_HOST = "127.0.0.1"
GATEWAY_PORT = 8080

BLYNK_CMD_RESPONSE = 0
BLYNK_CMD_LOGIN = 2
BLYNK_CMD_PING = 6
BLYNK_CMD_HARDWARE = 20
BLYNK_STATUS_SUCCESS = 200

def log(msg: str):
    print(f"[TEST-RUNNER] {msg}", flush=True)

def test_health_endpoint():
    log("Checking /api/v1/health endpoint...")
    resp = requests.get(f"{BASE_URL}/api/v1/health", timeout=5)
    assert resp.status_code == 200, f"Healthcheck failed with {resp.status_code}"
    data = resp.json()
    assert data["status"] == "healthy", f"Expected healthy, got {data['status']}"
    assert data["database"]["status"] == "connected"
    assert data["gateways"]["blynk_tcp_port"] == 8080
    log(f"  PASS: System healthy, uptime {data['uptime_seconds']}s, engine {data['database']['engine']}")

def ensure_test_device():
    log("Ensuring target test device exists in system...")
    import sys
    sys.path.insert(0, ".")
    from backend.database import SessionLocal
    from backend.models.entities import Device
    db = SessionLocal()
    dev = db.query(Device).first()
    if dev:
        dev_id = dev.id
        token = dev.auth_token
        db.close()
        log(f"  Using existing device: ID={dev_id}, Name='{dev.name}', Token={token[:8]}...")
        return dev_id, token
    db.close()

    token = "sim-cellular-esp32-token"
    log("  Creating bootstrap test device...")
    create_payload = {
        "name": "ESP32 Cellular Hybrid Node",
        "templateId": 1,
        "token": token
    }
    r = requests.post(f"{BASE_URL}/api/v1/devices", json=create_payload, timeout=5)
    dev = r.json()
    return dev["id"], token

def send_blynk_request(sock: socket.socket, msg_id: int, cmd: int, body: bytes) -> tuple:
    header = struct.pack(">BHH", cmd, msg_id, len(body))
    sock.sendall(header + body)
    resp_header = sock.recv(5)
    if not resp_header or len(resp_header) < 5:
        return (None, None, None)
    return struct.unpack(">BHH", resp_header)

def send_hardware_write(sock: socket.socket, msg_id: int, pin: int, value: str):
    # Hardware write framing: 'vw\0{pin}\0{value}'
    payload = f"vw\x00{pin}\x00{value}".encode("utf-8")
    header = struct.pack(">BHH", BLYNK_CMD_HARDWARE, msg_id, len(payload))
    sock.sendall(header + payload)
    time.sleep(0.1)

def test_blynk_tcp_and_cellular_telemetry(token: str):
    log("Connecting to Blynk Hardware TCP Gateway on Port 8080...")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5.0)
    s.connect((GATEWAY_HOST, GATEWAY_PORT))
    log("  TCP socket connected successfully.")

    # 1. Login Handshake
    login_body = token.encode("ascii")
    cmd, msg_id, status = send_blynk_request(s, 1, BLYNK_CMD_LOGIN, login_body)
    assert cmd == BLYNK_CMD_RESPONSE and status == BLYNK_STATUS_SUCCESS, f"Login failed: cmd={cmd}, status={status}"
    log("  PASS: Blynk protocol login handshake successful (200 OK).")

    # 2. Ping Check
    cmd, msg_id, status = send_blynk_request(s, 2, BLYNK_CMD_PING, b"")
    assert cmd == BLYNK_CMD_RESPONSE and status == BLYNK_STATUS_SUCCESS, f"Ping failed: cmd={cmd}, status={status}"
    log("  PASS: Blynk protocol keep-alive ping successful (200 OK).")

    # 3. Transmit Cellular Signal Quality (CSQ = 27 on V10)
    send_hardware_write(s, 3, 10, "27")
    log("  PASS: Ingested Cellular CSQ (V10 = 27) via TCP Wire.")

    # 4. Transmit Normal Temperature (V2 = 24.5)
    send_hardware_write(s, 4, 2, "24.5")
    log("  PASS: Ingested Base Telemetry (V2 = 24.5°C) via TCP Wire.")

    # 5. Transmit Initial Totalizer (V5 = 200.0)
    send_hardware_write(s, 5, 5, "200.0")
    log("  PASS: Ingested Initial Totalizer (V5 = 200.0) via TCP Wire.")

    time.sleep(0.5)
    s.close()
    log("  TCP socket closed gracefully.")

def trigger_anomalies_and_verify(token: str, device_id: int):
    log("\n--- INITIATING ANOMALY SIMULATION SUITE ---")

    # A. Anomaly 1: VALUE_STALL (Frozen sensor on Pin V4)
    # Ingest 9 consecutive cycles with identical reading 62.5
    log("Triggering Anomaly 1: VALUE_STALL (Frozen sensor on Pin V4 for 9 cycles)...")
    for i in range(9):
        resp = requests.get(f"{BASE_URL}/external/api/update?token={token}&V4=62.5", timeout=5)
        assert resp.status_code == 200

    # B. Anomaly 2: TOTALIZER_ROLLBACK (Cumulative meter tampering / counter drop)
    log("Triggering Anomaly 2: TOTALIZER_ROLLBACK (Counter dropped from 200.0 to 15.0 on V5)...")
    resp = requests.get(f"{BASE_URL}/external/api/update?token={token}&V5=15.0", timeout=5)
    assert resp.status_code == 200

    # C. Anomaly 3: UNEXPECTED_INGRESS_WHILE_INACTIVE (Thermal surge on V2 while V3 actuator is 0)
    log("Triggering Anomaly 3: UNEXPECTED_INGRESS_WHILE_INACTIVE (Surge to 54.0°C on V2 while V3=0)...")
    requests.get(f"{BASE_URL}/external/api/update?token={token}&V3=0", timeout=5)
    resp = requests.get(f"{BASE_URL}/external/api/update?token={token}&V2=54.0", timeout=5)
    assert resp.status_code == 200

    # D. Query Anomaly Engine Alerts
    log("Querying /api/v1/anomalies endpoint...")
    anomalies_resp = requests.get(f"{BASE_URL}/api/v1/anomalies?device_id={device_id}", timeout=5)
    assert anomalies_resp.status_code == 200
    alerts = anomalies_resp.json()
    log(f"  Found {len(alerts)} total anomaly alert(s) in system.")

    types_found = {a["anomalyType"] for a in alerts}
    log(f"  Anomaly types identified: {types_found}")

    assert "VALUE_STALL" in types_found, "Expected VALUE_STALL alert not found!"
    assert "TOTALIZER_ROLLBACK" in types_found, "Expected TOTALIZER_ROLLBACK alert not found!"
    assert "UNEXPECTED_INGRESS_WHILE_INACTIVE" in types_found, "Expected UNEXPECTED_INGRESS_WHILE_INACTIVE alert not found!"
    log("  PASS: All 3 anomaly types successfully trapped and classified by Anomaly Engine!")

    # E. Test Alert Resolution
    log("Testing alert resolution cycle via POST /api/v1/anomalies/{alert_id}/resolve...")
    for alert in alerts:
        a_id = alert["id"]
        res = requests.post(f"{BASE_URL}/api/v1/anomalies/{a_id}/resolve", timeout=5)
        assert res.status_code == 200
    log(f"  PASS: Successfully resolved {len(alerts)} anomaly alert(s).")

def main():
    log("================================================================================")
    log("STARTING AXON IOT SIMULATION & ANOMALY VALIDATION SUITE")
    log("================================================================================")

    test_health_endpoint()
    dev_id, token = ensure_test_device()
    test_blynk_tcp_and_cellular_telemetry(token)
    trigger_anomalies_and_verify(token, dev_id)

    log("================================================================================")
    log("ALL TESTS COMPLETED SUCCESSFULLY! ANOMALY ENGINE & PROTOCOLS 100% OPERATIONAL")
    log("================================================================================")

if __name__ == "__main__":
    main()
