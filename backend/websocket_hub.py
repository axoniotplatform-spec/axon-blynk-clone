import json
import logging
from typing import Dict, Set, Any
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.models.entities import Device, Datastream, DashboardWidget, TelemetryTimeSeries
from datetime import datetime

logger = logging.getLogger("axon.websocket")

class ShellBridgeHub:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket client connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket client disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast_event(self, event_name: str, payload: Any):
        """Broadcasts events like onValueUpdated, onConnectionChanged, onDevicesUpdated"""
        message = json.dumps({"event": event_name, "data": payload})
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                self.active_connections.discard(connection)

    async def handle_message(self, websocket: WebSocket, text: str):
        """Dispatches ShellBridge RPC method calls"""
        try:
            req = json.loads(text)
            req_id = req.get("id")
            method = req.get("method")
            params = req.get("params", {})
            
            db: Session = SessionLocal()
            result = None
            error = None

            try:
                if method == "getDevices":
                    devices = db.query(Device).all()
                    result = [
                        {
                            "id": d.id,
                            "name": d.name,
                            "status": d.status,
                            "templateId": d.template.template_id if d.template else None,
                            "templateName": d.template.name if d.template else None,
                            "firmwareVersion": d.firmware_version,
                            "lastReportedAt": d.last_reported_at.isoformat() if d.last_reported_at else None
                        }
                        for d in devices
                    ]

                elif method == "getDevice":
                    dev_id = params.get("selector")
                    d = db.query(Device).filter(Device.id == dev_id).first()
                    if d:
                        result = {
                            "id": d.id,
                            "name": d.name,
                            "status": d.status,
                            "authToken": d.auth_token,
                            "templateId": d.template.template_id if d.template else None,
                            "hardware": d.template.hardware_mcu if d.template else "ESP32",
                            "connection": d.template.connection_type if d.template else "WI_FI"
                        }
                    else:
                        error = {"code": "not_found", "message": f"Device {dev_id} not found"}

                elif method == "getDeviceDashboard":
                    dev_id = params.get("deviceId")
                    d = db.query(Device).filter(Device.id == dev_id).first()
                    if d and d.template:
                        widgets = db.query(DashboardWidget).filter(DashboardWidget.template_id == d.template_id).all()
                        datastreams = db.query(Datastream).filter(Datastream.template_id == d.template_id).all()
                        ds_map = {ds.pin: ds.current_value for ds in datastreams}

                        result = {
                            "deviceId": d.id,
                            "deviceName": d.name,
                            "status": d.status,
                            "widgets": [
                                {
                                    "id": w.id,
                                    "type": w.widget_type,
                                    "widgetType": w.widget_type,
                                    "label": w.label,
                                    "pin": w.pin,
                                    "currentValue": ds_map.get(w.pin, "0"),
                                    "grid": {"x": w.grid_x, "y": w.grid_y, "w": w.width, "h": w.height},
                                    "onLabel": w.on_label,
                                    "offLabel": w.off_label,
                                    "onColor": w.on_color,
                                    "offColor": w.off_color,
                                    "onBackColor": w.on_back_color,
                                    "offBackColor": w.off_back_color,
                                    "settings": w.settings
                                }
                                for w in widgets
                            ],
                            "datastreams": [
                                {
                                    "pin": ds.pin,
                                    "name": ds.name,
                                    "type": ds.data_type,
                                    "min": ds.min_value,
                                    "max": ds.max_value,
                                    "value": ds.current_value,
                                    "units": ds.units
                                }
                                for ds in datastreams
                            ]
                        }
                    else:
                        error = {"code": "not_found", "message": f"Device or dashboard not found"}

                elif method == "sendValue":
                    dev_id = params.get("deviceId")
                    pin = params.get("stream")
                    value = str(params.get("value"))

                    d = db.query(Device).filter(Device.id == dev_id).first()
                    if d:
                        # Update datastream
                        ds = db.query(Datastream).filter(
                            Datastream.template_id == d.template_id,
                            Datastream.pin == pin
                        ).first()
                        if ds:
                            ds.current_value = value
                            
                            # Record telemetry point
                            num_val = None
                            try:
                                num_val = float(value)
                            except ValueError:
                                pass

                            point = TelemetryTimeSeries(
                                device_id=d.id,
                                pin=pin,
                                value=value,
                                numeric_value=num_val,
                                timestamp=datetime.utcnow()
                            )
                            db.add(point)
                            db.commit()

                            result = {"success": True, "pin": pin, "value": value}
                            try:
                                from backend.hardware_gateway import hardware_gateway
                                asyncio.create_task(hardware_gateway.send_pin_write(d.auth_token, pin, value))
                            except Exception:
                                pass
                            
                            # Broadcast real-time update to all listeners
                            await self.broadcast_event("onValueUpdated", {
                                "deviceId": dev_id,
                                "stream": pin,
                                "value": value,
                                "timestamp": datetime.utcnow().isoformat()
                            })

                            # Phase 5B: Automations Rules Engine Evaluation
                            try:
                                from backend.rules_engine import evaluate_rules_for_device
                                evaluate_rules_for_device(db, dev_id, pin, value, hub=self)
                            except Exception as re_err:
                                logger.warning(f"Error evaluating rules: {re_err}")
                        else:
                            error = {"code": "invalid_pin", "message": f"Pin {pin} not registered on template"}
                    else:
                        error = {"code": "not_found", "message": "Device not found"}

                elif method == "getHistoryData":
                    options = params.get("options", {})
                    dev_id = options.get("deviceId")
                    pin = options.get("pin", "V0")
                    limit = int(options.get("limit", 100))

                    records = db.query(TelemetryTimeSeries).filter(
                        TelemetryTimeSeries.device_id == dev_id,
                        TelemetryTimeSeries.pin == pin
                    ).order_by(TelemetryTimeSeries.timestamp.desc()).limit(limit).all()

                    result = [
                        {
                            "timestamp": r.timestamp.isoformat(),
                            "value": r.value,
                            "numericValue": r.numeric_value
                        }
                        for r in reversed(records)
                    ]

                elif method == "getTheme":
                    result = {
                        "primary": "#10f17f",
                        "brand": "#d1ff39",
                        "bg": "#0a0a0f",
                        "cardBg": "#13131c",
                        "text": "#ffffff"
                    }

                else:
                    error = {"code": "unknown_method", "message": f"Method {method} not supported"}

            finally:
                db.close()

            response = {"id": req_id, "result": result, "error": error}
            await websocket.send_text(json.dumps(response))

        except Exception as e:
            logger.error(f"Error handling RPC: {e}")
            await websocket.send_text(json.dumps({
                "id": req.get("id") if 'req' in locals() else None,
                "error": {"code": "internal_error", "message": str(e)}
            }))

hub = ShellBridgeHub()
