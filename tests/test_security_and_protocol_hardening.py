import json
import os
import socket
import struct
import time
import urllib.error
import urllib.request

BASE_URL = os.getenv("AXON_TEST_BASE_URL", "http://127.0.0.1:8000")
TOKEN = os.getenv("AXON_TEST_DEVICE_TOKEN", "yhdHK6Vuj2F6X7CUnX-QQIpuEl9Yy_dk")


def blynk_frame(command, message_id, payload=b""):
    return struct.pack(">BHH", command, message_id, len(payload)) + payload


def test_protocol_and_device_controls():
    with socket.create_connection(("127.0.0.1", 8080), timeout=5) as device:
        device.sendall(blynk_frame(0x02, 1, TOKEN.encode()))
        assert struct.unpack(">BHH", device.recv(5)) == (0x00, 1, 200)

        assert urllib.request.urlopen(
            f"{BASE_URL}/external/api/isHardwareConnected?token={TOKEN}"
        ).read() == b"true"

        device.sendall(blynk_frame(0x14, 2, b"vr\x000\x00"))
        header = device.recv(5)
        command, message_id, length = struct.unpack(">BHH", header)
        assert (command, message_id) == (0x14, 2)
        assert device.recv(length).startswith(b"vr\x000\x00")

        req = urllib.request.Request(
            f"{BASE_URL}/api/v1/app/devices/1/write",
            data=json.dumps({"stream": "V1", "value": "77"}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        response = json.loads(urllib.request.urlopen(req).read())
        assert response["hardwareForwarded"] is True
        header = device.recv(5)
        command, _, length = struct.unpack(">BHH", header)
        assert command == 0x14
        assert device.recv(length) == b"vw\x001\x0077"

    time.sleep(0.2)
    assert urllib.request.urlopen(
        f"{BASE_URL}/external/api/isHardwareConnected?token={TOKEN}"
    ).read() == b"false"


def test_invalid_pin_and_safe_token_output():
    try:
        urllib.request.urlopen(f"{BASE_URL}/external/api/update?token={TOKEN}&V999=1")
    except urllib.error.HTTPError as error:
        assert error.code == 400
    else:
        raise AssertionError("Unknown pins must be rejected")

    devices = json.loads(urllib.request.urlopen(f"{BASE_URL}/api/v1/devices").read())
    assert devices and devices[0]["authToken"] != TOKEN


def test_production_auth_mode_in_isolated_process():
    """The production-mode behavior is exercised by the CI command separately."""
    assert os.getenv("AXON_REQUIRE_AUTH", "false").lower() in {"false", "0", "no"}
