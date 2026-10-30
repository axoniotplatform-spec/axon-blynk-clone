import socket
import struct
import sys
import time
import urllib.parse
import urllib.request

from tests._support import get_seeded_device_token


def recv_exact(sock, size):
    chunks = []
    received = 0
    while received < size:
        chunk = sock.recv(size - received)
        if not chunk:
            raise RuntimeError("short_response")
        chunks.append(chunk)
        received += len(chunk)
    return b"".join(chunks)


def main():
    stage = "seed_token"
    sock = None
    try:
        token = get_seeded_device_token()
        if not token:
            raise RuntimeError("missing_seeded_device")

        stage = "tcp_connect"
        sock = socket.create_connection(("127.0.0.1", 8080), timeout=5)
        sock.settimeout(5)

        stage = "blynk_login"
        token_bytes = token.encode("ascii")
        sock.sendall(struct.pack(">BHH", 0x02, 1, len(token_bytes)) + token_bytes)
        cmd, _msg_id, status = struct.unpack(">BHH", recv_exact(sock, 5))
        if (cmd, status) != (0x00, 200):
            raise RuntimeError("login_rejected")

        stage = "blynk_ping"
        sock.sendall(struct.pack(">BHH", 0x06, 2, 0))
        cmd, _msg_id, status = struct.unpack(">BHH", recv_exact(sock, 5))
        if (cmd, status) != (0x00, 200):
            raise RuntimeError("ping_rejected")

        stage = "v2_write"
        payload = b"vw\x002\x0036.8"
        sock.sendall(struct.pack(">BHH", 0x14, 3, len(payload)) + payload)
        time.sleep(0.75)

        def read_pin(pin):
            query = urllib.parse.urlencode({"token": token, "pin": pin})
            url = "http://127.0.0.1:8000/external/api/get?" + query
            with urllib.request.urlopen(url, timeout=5) as response:
                return response.read().decode("utf-8").strip()

        stage = "v2_api_readback"
        v2 = read_pin("V2")
        if v2 != "36.8":
            raise RuntimeError("v2_mismatch")

        stage = "v3_automation_readback"
        v3 = read_pin("V3")
        if v3 != "1":
            raise RuntimeError("v3_mismatch")

        stage = "socket_state_tracking_connected"
        is_conn_url = "http://127.0.0.1:8000/external/api/isHardwareConnected?" + urllib.parse.urlencode({"token": token})
        with urllib.request.urlopen(is_conn_url, timeout=5) as response:
            if response.read().decode("utf-8").strip().lower() != "true":
                raise RuntimeError("hardware_not_connected_in_state")

        print("BLYNK_LOGIN=PASS")
        print("BLYNK_PING=PASS")
        print("V2_TELEMETRY=PASS value=" + v2)
        print("V3_AUTOMATION=PASS value=" + v3)
        print("SOCKET_STATE_TRACKING=PASS (isHardwareConnected=true)")
        return 0
    except Exception as exc:
        print("LOCAL_PROTOCOL_FAILURE=" + stage + ":" + type(exc).__name__)
        return 1
    finally:
        if sock is not None:
            sock.close()
            time.sleep(0.5)
            try:
                with urllib.request.urlopen("http://127.0.0.1:8000/external/api/isHardwareConnected?" + urllib.parse.urlencode({"token": token}), timeout=5) as resp:
                    if resp.read().decode("utf-8").strip().lower() == "false":
                        print("SOCKET_STATE_DISCONNECT_CLEANUP=PASS (isHardwareConnected=false)")
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
