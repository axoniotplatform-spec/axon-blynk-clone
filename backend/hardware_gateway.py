import asyncio
import struct
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.models.entities import Device, Datastream, TelemetryTimeSeries
from backend.rules_engine import evaluate_rules_for_device

logger = logging.getLogger("axon.hardware_gateway")

# Blynk Protocol Constants
BLYNK_CMD_RESPONSE = 0x00
BLYNK_CMD_REGISTER = 0x01
BLYNK_CMD_LOGIN = 0x02
BLYNK_CMD_PING = 0x06
BLYNK_CMD_BRIDGE = 0x10
BLYNK_CMD_HARDWARE = 0x14
BLYNK_CMD_INTERNAL = 0x1D

BLYNK_STATUS_SUCCESS = 200
BLYNK_STATUS_INVALID_TOKEN = 9

class BlynkHardwareGateway:
    def __init__(self, host: str = "0.0.0.0", port: int = 8080, hub: Any = None):
        self.host = host
        self.port = port
        self.hub = hub
        self.connected_devices: Dict[str, asyncio.StreamWriter] = {}  # token -> writer
        self.device_info: Dict[str, Dict[str, Any]] = {}             # token -> {id, name, template_id}
        self.server: Optional[asyncio.AbstractServer] = None
        self._msg_id_counter = 1

    def next_msg_id(self) -> int:
        self._msg_id_counter = (self._msg_id_counter + 1) % 65535
        return self._msg_id_counter or 1

    async def start(self):
        self.server = await asyncio.start_server(self.handle_client, self.host, self.port)
        logger.info(f"[HardwareGateway] Blynk TCP Protocol Server listening on {self.host}:{self.port}")

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        peer = writer.get_extra_info('peername')
        logger.info(f"[HardwareGateway] New hardware TCP connection from {peer}")
        device_token: Optional[str] = None

        try:
            while True:
                # Read 5-byte Blynk header
                header = await reader.readexactly(5)
                cmd, msg_id, length = struct.unpack(">BHH", header)

                payload = b""
                if length > 0:
                    payload = await reader.readexactly(length)

                if cmd == BLYNK_CMD_LOGIN:
                    token = payload.decode('ascii', errors='ignore').strip('\x00').strip()
                    logger.info(f"[HardwareGateway] Login attempt with token: {token}")

                    db = SessionLocal()
                    try:
                        device = db.query(Device).filter(Device.auth_token == token).first()
                        if device:
                            device.status = "ONLINE"
                            device.last_heartbeat = datetime.utcnow()
                            db.commit()

                            device_token = token
                            self.connected_devices[token] = writer
                            self.device_info[token] = {
                                "id": device.id,
                                "name": device.name,
                                "template_id": device.template_id,
                                "org_id": device.org_id
                            }

                            # Send success response (200 OK)
                            resp = struct.pack(">BHH", BLYNK_CMD_RESPONSE, msg_id, BLYNK_STATUS_SUCCESS)
                            writer.write(resp)
                            await writer.drain()
                            logger.info(f"[HardwareGateway] Device '{device.name}' authenticated successfully.")

                            # Notify web console
                            if self.hub:
                                await self.hub.broadcast_event("onConnectionChanged", {
                                    "deviceId": device.id,
                                    "status": "ONLINE"
                                })
                        else:
                            logger.warning(f"[HardwareGateway] Invalid token: {token}")
                            resp = struct.pack(">BHH", BLYNK_CMD_RESPONSE, msg_id, BLYNK_STATUS_INVALID_TOKEN)
                            writer.write(resp)
                            await writer.drain()
                            break
                    finally:
                        db.close()

                elif cmd == BLYNK_CMD_PING:
                    resp = struct.pack(">BHH", BLYNK_CMD_RESPONSE, msg_id, BLYNK_STATUS_SUCCESS)
                    writer.write(resp)
                    await writer.drain()

                elif cmd == BLYNK_CMD_HARDWARE:
                    if not device_token or device_token not in self.device_info:
                        continue

                    d_info = self.device_info[device_token]
                    parts = payload.split(b'\0')
                    if len(parts) >= 3 and parts[0] == b'vw':
                        # Virtual pin write: vw\0<pin>\0<val>
                        pin_num = parts[1].decode('ascii', errors='ignore')
                        val_str = parts[2].decode('utf-8', errors='ignore')
                        pin_name = f"V{pin_num}"

                        db = SessionLocal()
                        try:
                            ds = db.query(Datastream).filter(
                                Datastream.template_id == d_info["template_id"],
                                Datastream.pin == pin_name
                            ).first()
                            if ds:
                                ds.current_value = val_str
                                db.commit()

                                # Record time series
                                try:
                                    t_val = float(val_str)
                                    db.add(TelemetryTimeSeries(
                                        device_id=d_info["id"],
                                        pin=pin_name,
                                        value=t_val
                                    ))
                                    db.commit()
                                except Exception:
                                    pass

                                # Broadcast to Web Console UI in real time
                                if self.hub:
                                    await self.hub.broadcast_event("onValueUpdated", {
                                        "deviceId": d_info["id"],
                                        "stream": pin_name,
                                        "value": val_str
                                    })

                                # Evaluate Automations Rules Engine
                                evaluate_rules_for_device(db, d_info["id"], pin_name, val_str, hub=self.hub)
                        finally:
                            db.close()

                elif cmd == BLYNK_CMD_INTERNAL:
                    # Sync RTC / epoch time
                    epoch = int(datetime.utcnow().timestamp())
                    body = f"rtc\0{epoch}".encode('ascii')
                    resp = struct.pack(">BHH", BLYNK_CMD_INTERNAL, msg_id, len(body)) + body
                    writer.write(resp)
                    await writer.drain()

        except (asyncio.IncompleteReadError, ConnectionResetError, BrokenPipeError):
            logger.info(f"[HardwareGateway] Client disconnected: {peer}")
        except Exception as e:
            logger.error(f"[HardwareGateway] Protocol error: {e}")
        finally:
            if device_token and device_token in self.connected_devices:
                del self.connected_devices[device_token]
                db = SessionLocal()
                try:
                    dev = db.query(Device).filter(Device.auth_token == device_token).first()
                    if dev:
                        dev.status = "OFFLINE"
                        db.commit()
                        if self.hub:
                            asyncio.ensure_future(self.hub.broadcast_event("onConnectionChanged", {
                                "deviceId": dev.id,
                                "status": "OFFLINE"
                            }))
                finally:
                    db.close()
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def send_pin_write(self, token: str, pin: str, value: Any) -> bool:
        """
        Sends hardware actuation command down to connected ESP32/ESP8266 client.
        """
        if token not in self.connected_devices:
            return False

        writer = self.connected_devices[token]
        pin_num = pin.upper().replace("V", "")
        body = f"vw\0{pin_num}\0{value}".encode('utf-8')
        frame = struct.pack(">BHH", BLYNK_CMD_HARDWARE, self.next_msg_id(), len(body)) + body

        try:
            writer.write(frame)
            await writer.drain()
            return True
        except Exception as e:
            logger.error(f"[HardwareGateway] Failed to send hardware frame: {e}")
            return False

# Global gateway instance
hardware_gateway = BlynkHardwareGateway()
