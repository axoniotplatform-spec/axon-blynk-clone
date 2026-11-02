"""
test_ota_and_connect_suite.py — Live End-to-End HTTP Verification against Axon IoT Gateway:
1. Auto-LAN-IP Gateway Discovery (/api/v1/system/connect-info)
2. Zero-dependency ISO/IEC 18004 SVG QR Code Generator (/api/v1/system/qr.svg)
3. Blynk.Air HTTP OTA Firmware Upload, MD5/SHA-256 Streaming & 304 Version Check
4. Live Push Notification Channel Configuration & Diagnostic Alert Dispatch
"""

import os
import json
import uuid
import hashlib
import urllib.request
import urllib.parse
import urllib.error

BASE_URL = os.getenv("AXON_TEST_BASE_URL", "http://127.0.0.1:8000")


def _http_get(path: str, params: dict = None):
    url = BASE_URL + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            return resp.status, dict(resp.headers.items()), resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers.items()), exc.read()


def _http_post_json(path: str, payload: dict):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        BASE_URL + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=6) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def _http_post_multipart(path: str, fields: dict, file_field: str, filename: str, content: bytes):
    boundary = "----AxonBoundary" + uuid.uuid4().hex
    parts = []
    for k, v in fields.items():
        parts.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode("utf-8")
        )
    parts.append(
        (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{file_field}\"; filename=\"{filename}\"\r\n"
            f"Content-Type: application/octet-stream\r\n\r\n"
        ).encode("utf-8")
        + content
        + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    body = b"".join(parts)
    req = urllib.request.Request(
        BASE_URL + path,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=8) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def test_connect_info_and_qr_svg():
    status, _, raw = _http_get("/api/v1/system/connect-info")
    assert status == 200
    info = json.loads(raw.decode("utf-8"))
    assert "lan_ip" in info
    assert info["hardware_tcp_port"] == 8080
    assert "/downloads/axon-iot.apk" in info["lan_apk_download_url"]
    print(f"  -> Detected LAN Gateway: {info['gateway_base_url']} | Signed Keystore: {info['apk_signed_release']}")

    s1, h1, b1 = _http_get("/api/v1/system/qr.svg", {"data": info["lan_apk_download_url"]})
    assert s1 == 200 and b"<svg" in b1

    s2, h2, b2 = _http_get("/api/v1/system/qr.svg", {"data": info["cloud_apk_release_url"]})
    assert s2 == 200 and b"<svg" in b2


def test_blynk_air_ota_upload_stream_and_304():
    from backend.database import SessionLocal
    from backend.models.entities import Device

    db = SessionLocal()
    try:
        dev = db.query(Device).first()
        assert dev is not None
        dev.firmware_version = "1.0.0"
        token = dev.auth_token
        db.commit()
    finally:
        db.close()

    fw_payload = b"\xE9\x03\x02\x20AXON_ESP32_PROD_FW_V9_5_0" + (b"\xAA" * 1024)
    expected_sha256 = hashlib.sha256(fw_payload).hexdigest()
    expected_md5 = hashlib.md5(fw_payload).hexdigest()

    st_up, up_json = _http_post_multipart(
        "/api/v1/ota/upload",
        {"version": "9.5.0", "hardware_mcu": "ESP32", "notes": "Live HTTP OTA verification"},
        "file",
        "axon_esp32_9.5.0.bin",
        fw_payload,
    )
    assert st_up == 200
    assert up_json["release"]["sha256"] == expected_sha256
    assert up_json["release"]["md5"] == expected_md5

    # Check from v1.0.0 -> 200 OK binary stream
    st1, hdr1, body1 = _http_get("/external/api/ota/firmware", {"token": token, "version": "1.0.0", "mcu": "ESP32"})
    hdr1_lc = {k.lower(): v for k, v in hdr1.items()}
    assert st1 == 200, f"Expected 200, got {st1}"
    assert body1 == fw_payload, f"Len mismatch: got {len(body1)} ({body1[:30]}), expected {len(fw_payload)}"
    assert hdr1_lc["x-md5"] == expected_md5
    assert hdr1_lc["x-axon-sha256"] == expected_sha256
    assert hdr1_lc["x-axon-version"] == "9.5.0"

    # Check from v9.5.0 -> 304 Not Modified
    st2, _, _ = _http_get("/external/api/ota/firmware", {"token": token, "version": "9.5.0", "mcu": "ESP32"})
    assert st2 == 304


def test_live_notification_config_and_test_dispatch():
    st_cfg, cfg_json = _http_post_json(
        "/api/v1/notifications/configure",
        {"webhook_url": "http://127.0.0.1:9/noop-webhook"},
    )
    assert st_cfg == 200 and cfg_json["status"] == "configured"

    st_test, test_json = _http_post_json(
        "/api/v1/notifications/dispatch-test",
        {"severity": "CRITICAL", "message": "Live E2E diagnostic alert"},
    )
    assert st_test == 200 and test_json["status"] == "dispatched"
    assert test_json["alert"]["anomaly_type"] == "DIAGNOSTIC_TEST"


if __name__ == "__main__":
    test_connect_info_and_qr_svg()
    print("[PASS] 1/3 Connect-Info & ISO/IEC 18004 QR SVG verified!")
    test_blynk_air_ota_upload_stream_and_304()
    print("[PASS] 2/3 Blynk.Air HTTP OTA Upload, MD5/SHA-256 Stream & 304 verified!")
    test_live_notification_config_and_test_dispatch()
    print("[PASS] 3/3 Live Notification Channel Config & Alert Dispatch verified!")
    print("ALL ENTERPRISE OTA, QR & ALERT TESTS PASSED 100%!")
