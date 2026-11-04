"""
simulator_service.py — Embedded Async Multi-Device Blynk Binary TCP Telemetry Simulator.
Connects directly to Axon IoT's TCP Port 8080 using raw Blynk v1 binary wire framing
(0x02 LOGIN, 0x14 HARDWARE 'vw', 0x06 PING) so Web Console & Mobile App gauges and
SuperCharts animate smoothly in real time.
"""

import os
import math
import time
import struct
import asyncio
import logging
from typing import Dict, Any, Optional
from backend.database import SessionLocal
from backend.models.entities import Device

logger = logging.getLogger("axon.simulator")

CMD_LOGIN = 2
CMD_PING = 6
CMD_HARDWARE = 20


def pack_blynk_frame(cmd: int, msg_id: int, payload: bytes) -> bytes:
    return struct.pack("!BHH", cmd, msg_id, len(payload)) + payload


class LiveFleetSimulatorService:
    def __init__(self):
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None
        self._frames_sent: int = 0
        self._started_at: Optional[float] = None
        self._interval_sec: float = 2.0
        self._active_nodes: int = 0

    def status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "active_nodes": self._active_nodes if self._running else 0,
            "frames_sent": self._frames_sent,
            "interval_sec": self._interval_sec,
            "uptime_sec": round(time.time() - self._started_at, 1) if (self._running and self._started_at) else 0.0,
        }

    def start(self, interval_sec: float = 2.0) -> Dict[str, Any]:
        self._interval_sec = max(0.5, min(interval_sec, 30.0))
        if not self._running:
            self._running = True
            self._started_at = time.time()
            self._task = asyncio.create_task(self._run_loop())
        return self.status()

    async def stop(self) -> Dict[str, Any]:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        self._active_nodes = 0
        return self.status()

    async def _simulate_single_device(self, token: str, phase_offset: float, host: str, port: int):
        msg_id = 1
        while self._running:
            writer = None
            try:
                reader, writer = await asyncio.open_connection(host, port)
                # 0x02 LOGIN handshake
                writer.write(pack_blynk_frame(CMD_LOGIN, msg_id, token.encode("utf-8")))
                await writer.drain()
                resp = await asyncio.wait_for(reader.read(5), timeout=3.0)
                if len(resp) < 5:
                    raise ConnectionError("Short Blynk LOGIN response")

                tick = 0
                while self._running:
                    t = time.time() + phase_offset
                    temp_v2 = round(26.8 + 2.9 * math.sin(t / 6.0), 2)
                    hum_v5 = int(round(58 + 9 * math.cos(t / 8.5)))
                    pwm_v1 = int(round(145 + 75 * math.sin(t / 5.0)))
                    csq_v10 = int(round(25 + 4 * math.sin(t / 11.0)))

                    for pin_num, val in (("2", str(temp_v2)), ("5", str(hum_v5)), ("1", str(pwm_v1)), ("10", str(csq_v10))):
                        msg_id = (msg_id % 65000) + 1
                        body = f"vw\x00{pin_num}\x00{val}".encode("utf-8")
                        writer.write(pack_blynk_frame(CMD_HARDWARE, msg_id, body))
                        self._frames_sent += 1

                    if tick % 5 == 0:
                        msg_id = (msg_id % 65000) + 1
                        writer.write(pack_blynk_frame(CMD_PING, msg_id, b""))
                        try:
                            await asyncio.wait_for(reader.read(5), timeout=1.0)
                        except asyncio.TimeoutError:
                            pass

                    await writer.drain()
                    tick += 1
                    await asyncio.sleep(self._interval_sec)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.debug(f"[Simulator] Reconnecting token {token[:6]}...: {exc}")
                await asyncio.sleep(2.0)
            finally:
                if writer is not None:
                    try:
                        writer.close()
                        await writer.wait_closed()
                    except Exception:
                        pass

    async def _run_loop(self):
        hw_port = int(os.getenv("AXON_HARDWARE_PORT", "8080"))
        db = SessionLocal()
        try:
            tokens = [d.auth_token for d in db.query(Device).limit(5).all() if d.auth_token]
        finally:
            db.close()

        if not tokens:
            self._running = False
            return

        self._active_nodes = len(tokens)
        workers = [
            asyncio.create_task(self._simulate_single_device(tok, idx * 1.7, "127.0.0.1", hw_port))
            for idx, tok in enumerate(tokens)
        ]
        try:
            await asyncio.gather(*workers)
        except asyncio.CancelledError:
            for w in workers:
                w.cancel()
            raise


fleet_simulator = LiveFleetSimulatorService()
