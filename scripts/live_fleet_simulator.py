#!/usr/bin/env python3
"""
live_fleet_simulator.py — Standalone CLI Multi-Device Blynk TCP Telemetry Simulator.
Streams live sinusoidal industrial sensor frames (Temperature V2, Humidity V5, PWM V1, CSQ V10)
over raw TCP port 8080 against any local or remote Axon IoT Gateway.

Usage:
    python scripts/live_fleet_simulator.py --host 127.0.0.1 --port 8080 --duration 30
"""

import argparse
import asyncio
import math
import struct
import time

CMD_LOGIN = 2
CMD_PING = 6
CMD_HARDWARE = 20


def pack_frame(cmd: int, msg_id: int, payload: bytes) -> bytes:
    return struct.pack("!BHH", cmd, msg_id, len(payload)) + payload


async def run_cli_simulator(host: str, port: int, token: str, duration: float, interval: float):
    print(f"[Axon CLI Simulator] Connecting to {host}:{port} with token {token[:8]}...")
    reader, writer = await asyncio.open_connection(host, port)
    writer.write(pack_frame(CMD_LOGIN, 1, token.encode("utf-8")))
    await writer.drain()
    ack = await asyncio.wait_for(reader.read(5), timeout=5.0)
    print(f"[Axon CLI Simulator] Handshake ACK received ({len(ack)} bytes). Streaming live telemetry...")

    start = time.time()
    msg_id = 2
    sent = 0
    try:
        while duration <= 0 or (time.time() - start) < duration:
            t = time.time()
            temp = round(26.5 + 3.0 * math.sin(t / 5.0), 2)
            hum = int(round(60 + 8 * math.cos(t / 7.0)))
            for pin, val in (("2", str(temp)), ("5", str(hum))):
                body = f"vw\x00{pin}\x00{val}".encode("utf-8")
                writer.write(pack_frame(CMD_HARDWARE, msg_id, body))
                msg_id = (msg_id % 65000) + 1
                sent += 1
            await writer.drain()
            print(f"  -> Streamed V2={temp}°C, V5={hum}% (total frames={sent})")
            await asyncio.sleep(interval)
    finally:
        writer.close()
        await writer.wait_closed()
        print(f"[Axon CLI Simulator] Closed cleanly after {sent} frames.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Axon IoT Multi-Pin Blynk TCP Simulator")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--token", default="yhdHK6Vuj2F6X7CUnX-QQIpuEl9Yy_dk")
    parser.add_argument("--duration", type=float, default=10.0, help="Seconds to run (0 = infinite)")
    parser.add_argument("--interval", type=float, default=1.5)
    args = parser.parse_args()
    asyncio.run(run_cli_simulator(args.host, args.port, args.token, args.duration, args.interval))
