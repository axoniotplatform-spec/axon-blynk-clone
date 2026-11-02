"""
anomaly_engine.py — Axon IoT Core Industrial Fault & Anomaly Detection Engine
Adapted from Omiru Industrial Systems architecture.

Provides real-time mathematical and state-machine anomaly evaluation during telemetry ingestion:
1. UNEXPECTED_INGRESS_WHILE_INACTIVE (leaks, phantom loads, valve bypass)
2. VALUE_STALL (pipe clog, frozen sensor, deadhead protection)
3. TOTALIZER_ROLLBACK (meter tampering, counter reset)
4. DEVICE_HEALTH_SWEEP (heartbeat stall, offline state transition)
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from collections import defaultdict
from sqlalchemy.orm import Session
from backend.models.entities import Device, Datastream, AnomalyAlert
from backend.notification_service import dispatch_anomaly_notification

logger = logging.getLogger("axon.anomaly_engine")

# In-memory circular buffer for telemetry history per device pin
# Format: device_pin_history[device_id][pin] = [list of (timestamp, value)]
_device_pin_history: Dict[int, Dict[int, List[float]]] = defaultdict(lambda: defaultdict(list))
_max_history_len = 15

def run_anomaly_checks(db: Session, device: Device, pin: int, value_str: str, hub: Any = None) -> List[Dict[str, Any]]:
    """
    Evaluates telemetry ingress for real-time operational faults and anomalies.
    Returns a list of detected anomalies.
    """
    detected_anomalies: List[Dict[str, Any]] = []

    try:
        val = float(value_str)
    except (ValueError, TypeError):
        return detected_anomalies

    device_id = device.id
    history = _device_pin_history[device_id][pin]
    history.append(val)
    if len(history) > _max_history_len:
        history.pop(0)

    # 0. Unauthorized Ingress on Inactive / Maintenance Device
    if getattr(device, "status", "") in ("INACTIVE", "DISABLED", "MAINTENANCE"):
        alert = AnomalyAlert(
            device_id=device_id,
            anomaly_type="UNEXPECTED_INGRESS_WHILE_INACTIVE",
            severity="CRITICAL",
            message=f"Unauthorized telemetry ingress received while device status is '{device.status}'",
            pin=pin,
            value=val
        )
        db.add(alert)
        db.commit()
        try:
            dispatch_anomaly_notification(db, device_id, "UNEXPECTED_INGRESS_WHILE_INACTIVE", "CRITICAL", alert.message, pin, val)
        except Exception as e:
            logger.warning(f"[AnomalyEngine] Failed to dispatch notification: {e}")
        detected_anomalies.append({
            "type": "UNEXPECTED_INGRESS_WHILE_INACTIVE",
            "pin": pin,
            "value": val
        })
        logger.warning(f"[AnomalyEngine] UNEXPECTED_INGRESS on Inactive Device {device_id}: status={device.status}")

    # 1. Totalizer Rollback Detection
    # If a datastream is a cumulative counter (e.g. volume, energy, total hours) and drops
    if len(history) >= 2:
        prev_val = history[-2]
        # Drop detection (only applies if previous value was substantial)
        if prev_val > 5.0 and val < (prev_val * 0.7):
            alert = AnomalyAlert(
                device_id=device_id,
                anomaly_type="TOTALIZER_ROLLBACK",
                severity="CRITICAL",
                message=f"Cumulative totalizer rollback detected on Pin V{pin}: dropped from {prev_val:.2f} to {val:.2f}",
                pin=pin,
                value=val
            )
            db.add(alert)
            db.commit()
            try:
                dispatch_anomaly_notification(db, device_id, "TOTALIZER_ROLLBACK", "CRITICAL", alert.message, pin, val)
            except Exception as e:
                logger.warning(f"[AnomalyEngine] Failed to dispatch notification: {e}")
            detected_anomalies.append({
                "type": "TOTALIZER_ROLLBACK",
                "pin": pin,
                "prev": prev_val,
                "current": val
            })
            logger.warning(f"[AnomalyEngine] TOTALIZER_ROLLBACK on Device {device_id} Pin V{pin}: {prev_val} -> {val}")

    # 2. Value Stall Detection
    # If dynamic sensor produces identical reading for 8 consecutive ingress cycles
    if len(history) >= 8 and val > 0:
        if all(abs(h - val) < 1e-4 for h in history[-8:]):
            alert = AnomalyAlert(
                device_id=device_id,
                anomaly_type="VALUE_STALL",
                severity="WARNING",
                message=f"Sensor value freeze/stall detected on Pin V{pin}: frozen at {val:.2f} for 8 consecutive cycles",
                pin=pin,
                value=val
            )
            db.add(alert)
            db.commit()
            try:
                dispatch_anomaly_notification(db, device_id, "VALUE_STALL", "WARNING", alert.message, pin, val)
            except Exception as e:
                logger.warning(f"[AnomalyEngine] Failed to dispatch notification: {e}")
            detected_anomalies.append({
                "type": "VALUE_STALL",
                "pin": pin,
                "value": val
            })
            logger.warning(f"[AnomalyEngine] VALUE_STALL on Device {device_id} Pin V{pin}: frozen at {val}")

    # 3. Unexpected Flow / Current While Inactive
    # If Pin V3 (Fan / Relay / Pump) is 0, but Pin V2 (Temp/Power/Flow) indicates aggressive surging
    if pin == 2 and val > 45.0:
        # Check actuator state (pin 3) on device template
        actuator_ds = db.query(Datastream).filter(
            Datastream.template_id == device.template_id,
            Datastream.pin.in_(["V3", "3"])
        ).first()
        if (not actuator_ds) or (actuator_ds.current_value in ("0", "0.0", "OFF")):
            alert = AnomalyAlert(
                device_id=device_id,
                anomaly_type="UNEXPECTED_INGRESS_WHILE_INACTIVE",
                severity="CRITICAL",
                message=f"Critical high temperature surge ({val:.1f}°C) observed while cooling actuator V3 is commanded OFF",
                pin=pin,
                value=val
            )
            db.add(alert)
            db.commit()
            try:
                dispatch_anomaly_notification(db, device_id, "UNEXPECTED_INGRESS_WHILE_INACTIVE", "CRITICAL", alert.message, pin, val)
            except Exception as e:
                logger.warning(f"[AnomalyEngine] Failed to dispatch notification: {e}")
            detected_anomalies.append({
                "type": "UNEXPECTED_INGRESS_WHILE_INACTIVE",
                "pin": pin,
                "value": val
            })
            logger.warning(f"[AnomalyEngine] UNEXPECTED_INGRESS on Device {device_id}: V2={val} while V3=0")

    # Broadcast to real-time UI hub if any anomalies were caught
    if detected_anomalies and hub:
        try:
            import asyncio
            asyncio.create_task(hub.broadcast_json({
                "type": "ANOMALY_ALERTS",
                "device_id": device_id,
                "anomalies": detected_anomalies
            }))
        except Exception:
            pass

    return detected_anomalies

def sweep_device_health(db: Session, timeout_seconds: int = 90, hub: Any = None) -> int:
    """
    Sweeps all devices and transitions any with expired last_seen to offline.
    """
    now = datetime.utcnow()
    cutoff = now - timedelta(seconds=timeout_seconds)
    stale_devices = db.query(Device).filter(Device.is_online == True, Device.last_seen < cutoff).all()
    count = 0
    for dev in stale_devices:
        dev.is_online = False
        count += 1
    if count > 0:
        db.commit()
        logger.info(f"[AnomalyEngine] Health sweep marked {count} stale device(s) as OFFLINE")
        if hub:
            try:
                import asyncio
                asyncio.create_task(hub.broadcast_json({
                    "type": "DEVICE_HEALTH_SWEEP",
                    "stale_count": count
                }))
            except Exception:
                pass
    return count
