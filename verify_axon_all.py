#!/usr/bin/env python3
"""Master verification suite for Manus 2.0 to verify all Axon IoT / Blynk parity layers."""

import os
import sys
import json
import time
import shutil
import socket
import datetime
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT if (ROOT / "backend").is_dir() else (ROOT / "axon-blynk-clone")

# Resolve Python executable
PYTHON = Path(sys.executable)
work_py = Path(r"C:\Users\USER\Downloads\MANUS TEST\.work\runtime-env\Scripts\python.exe")
if work_py.is_file():
    PYTHON = work_py

# Resolve Database URL
env = os.environ.copy()
if "DATABASE_URL" not in env:
    disp_db = Path(r"C:\Users\USER\Downloads\MANUS TEST\.work\runtime-disposable.sqlite")
    if disp_db.is_file():
        env["DATABASE_URL"] = f"sqlite:///{disp_db.as_posix()}"
    else:
        env["DATABASE_URL"] = f"sqlite:///{(REPO / 'axon_iot.db').as_posix()}"

env["PYTHONPATH"] = str(REPO)
env["PYTHONIOENCODING"] = "utf-8"
env["PYTHONUTF8"] = "1"

def check_tcp(host, port, timeout=2.0):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

def check_http(url, timeout=3.0):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False

def check_ws_upgrade(host, port, timeout=3.0):
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        req = (
            f"GET / HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n"
            f"Sec-WebSocket-Version: 13\r\n\r\n"
        )
        s.sendall(req.encode("ascii"))
        res = s.recv(1024).decode("latin1", errors="ignore")
        s.close()
        return "101 Switching Protocols" in res
    except Exception:
        return False

def run_step(title, cmd):
    print(f"\n================================================================================")
    print(f"RUNNING: {title}")
    print(f"COMMAND: {' '.join(cmd)}")
    print(f"================================================================================")
    res = subprocess.run(cmd, env=env, text=True, capture_output=True)
    if res.stdout:
        print(res.stdout.strip())
    if res.stderr:
        print(res.stderr.strip(), file=sys.stderr)
    return res.returncode == 0

def main():
    print("=" * 80)
    print("AXON IOT / BLYNK CLONE — FULL AUTOMATED VERIFICATION SUITE")
    print(f"Target Repo : {REPO}")
    print(f"Python Path : {PYTHON}")
    print(f"Database    : {env['DATABASE_URL']}")
    print("=" * 80)

    results = {}

    # 1. Port & Protocol Reachability (HTTP, TCP)
    print("\n[STEP 1/5] Verifying Services, HTTP Endpoints & Protocol Sockets...")
    p8000 = check_http("http://127.0.0.1:8000/docs")
    p8080 = check_tcp("127.0.0.1", 8080)
    p9011 = check_tcp("127.0.0.1", 9011)

    print(f" - Port 8000 (Axon Core HTTP API /docs) : {'PASS (200 OK)' if p8000 else 'FAIL'}")
    print(f" - Port 8080 (Blynk TCP Hardware Socket): {'PASS (Connected)' if p8080 else 'FAIL'}")
    print(f" - Port 9011 (Wokwi Gateway TCP Socket) : {'PASS (Connected)' if p9011 else 'FAIL'}")
    results["Port & Protocol Reachability (8000 HTTP, 8080 TCP, 9011 TCP)"] = p8000 and p8080 and p9011

    # 2. Hardware TCP Protocol & Sync Test
    script_sync = REPO / "tests" / "test_hardware_and_sync_verification.py"
    ok_sync = run_step(
        "Backend HTTP Routes, Hardware TCP Protocol & Unified User Sync",
        [str(PYTHON), str(script_sync)]
    )
    results["Hardware Protocol & User Directory Sync"] = ok_sync

    # 3. Automations Engine Test
    script_auto = REPO / "tests" / "test_automations_engine.py"
    ok_auto = run_step(
        "Automations Engine & Threshold Trigger (V2 > 30°C -> V3 Relay ON)",
        [str(PYTHON), str(script_auto)]
    )
    results["Automations Engine & Rule Execution"] = ok_auto

    # 4. Standalone Binary Protocol Probe
    script_probe = REPO / "tests" / "probe_protocol.py"
    if not script_probe.is_file():
        script_probe = Path(r"C:\Users\USER\Downloads\MANUS TEST\.work\axon-iot-parity-20261023\probe_protocol.py")

    ok_probe = run_step(
        "Byte-Level Blynk Binary Protocol Probe (Login, Ping, Telemetry, Socket Tracking)",
        [str(PYTHON), str(script_probe)]
    )
    results["Blynk Binary Protocol & Socket Tracking"] = ok_probe

    # 5. ESP32 Firmware Build Check
    print("\n================================================================================")
    print("RUNNING: ESP32 Official Blynk Firmware Compilation (PlatformIO)")
    print("================================================================================")
    import tempfile
    with tempfile.TemporaryDirectory(prefix="axon-verify-build-") as tmp:
        proj = Path(tmp) / "project"
        shutil.copytree(REPO / "wokwi", proj)
        sketch = proj / "src" / "main.cpp"
        src = sketch.read_text(encoding="utf-8")
        sketch.write_text(src.replace("__AXON_TEST_DEVICE_TOKEN__", '"test_device_token_verify"'), encoding="utf-8")
        
        pio_bin = shutil.which("pio") or str(Path(r"C:\Users\USER\Downloads\MANUS TEST\.work\runtime-env\Scripts\pio.exe"))
        cmd = [str(pio_bin), "run", "--project-dir", str(proj)]
        res = subprocess.run(cmd, env=env, text=True, capture_output=True)
        bin_ok = (proj / ".pio" / "build" / "esp32dev" / "firmware.bin").is_file()
        if bin_ok and res.returncode == 0:
            print("[PASS] ESP32 firmware cleanly built with official Blynk 1.4.0 (firmware.bin generated).")
            results["ESP32 Official Blynk Firmware Build (.bin)"] = True
        else:
            print("[FAIL] ESP32 firmware build failed.")
            if res.stdout:
                print(res.stdout[-1000:])
            results["ESP32 Official Blynk Firmware Build (.bin)"] = False

    # Save artifact receipt
    artifact_dir = REPO / "tests" / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    receipt = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "target_repo": str(REPO),
        "results": results,
        "overall_pass": all(results.values())
    }
    receipt_file = artifact_dir / "verification_receipt.json"
    receipt_file.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(f"\n[INFO] Verification artifact receipt written to: {receipt_file}")

    # Final Summary Matrix
    print("\n" + "=" * 80)
    print("FINAL VERIFICATION SUMMARY MATRIX")
    print("=" * 80)
    all_passed = True
    for test_name, passed in results.items():
        status_str = "PASS [100%]" if passed else "FAIL"
        print(f" {test_name:<55} : {status_str}")
        if not passed:
            all_passed = False

    print("=" * 80)
    if all_passed:
        print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY WITH 100% PASS RATE!")
        return 0
    else:
        print("SOME VERIFICATIONS FAILED. PLEASE REVIEW LOGS ABOVE.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
