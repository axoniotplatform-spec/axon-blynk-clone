import urllib.request
import json

TOKEN = "yhdHK6Vuj2F6X7CUnX-QQIpuEl9Yy_dk"

def test_automations():
    print("--- TEST 1: List Automations ---")
    res = urllib.request.urlopen("http://127.0.0.1:8000/api/v1/automations")
    rules = json.loads(res.read().decode())
    print(f"Found {len(rules)} automation rules:")
    for r in rules:
        print(f" - {r['name']} | Cond: {r['condition']} | Action: {r['action']} | Active: {r['isActive']}")

    print("\n--- TEST 2: External Blynk API GET & Connectivity ---")
    is_conn = urllib.request.urlopen(f"http://127.0.0.1:8000/external/api/isHardwareConnected?token={TOKEN}").read().decode()
    print(f"isHardwareConnected: {is_conn}")

    temp_val = urllib.request.urlopen(f"http://127.0.0.1:8000/external/api/get?token={TOKEN}&pin=V2").read().decode()
    print(f"Initial V2 (Temperature): {temp_val}")

    # Reset V3 to 0 first to verify automation actuates it
    urllib.request.urlopen(f"http://127.0.0.1:8000/external/api/update?token={TOKEN}&V3=0")
    fan_reset = urllib.request.urlopen(f"http://127.0.0.1:8000/external/api/get?token={TOKEN}&pin=V3").read().decode()
    print(f"V3 after reset to 0: {fan_reset}")
    assert fan_reset == "0", f"Expected V3 to be 0, got {fan_reset}"

    print("\n--- TEST 3: Trigger Rules Engine via High Temperature (V2=34.2 > 30) ---")
    update_resp = urllib.request.urlopen(f"http://127.0.0.1:8000/external/api/update?token={TOKEN}&V2=34.2").read().decode()
    print(f"Update response: {update_resp}")

    # Check if V3 automatically became 1
    fan_after_rule = urllib.request.urlopen(f"http://127.0.0.1:8000/external/api/get?token={TOKEN}&pin=V3").read().decode()
    print(f"AUTOMATION RESULT -> V3 (Fan Relay) is now: {fan_after_rule}")
    assert fan_after_rule == "1", f"Expected V3 to be 1, got {fan_after_rule}"
    print(">>> SUCCESS! Automation rule automatically triggered Fan Relay V3=1 upon V2=34.2! <<<")

if __name__ == "__main__":
    test_automations()
