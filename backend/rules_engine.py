import re
import logging
from typing import Any, List, Dict
from sqlalchemy.orm import Session
from backend.models.entities import AutomationRule, Device, Datastream, TelemetryTimeSeries

logger = logging.getLogger("axon.rules_engine")

def evaluate_rules_for_device(db: Session, device_id: int, pin: str, new_value: Any, hub: Any = None) -> List[Dict[str, Any]]:
    """
    Evaluates all active automation rules when a datastream value changes on a device.
    Executes actions (e.g., turning on a fan relay, alerting) and dispatches real-time events.
    """
    triggered_actions = []
    
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        return triggered_actions

    # Fetch active rules
    rules = db.query(AutomationRule).filter(
        AutomationRule.org_id == device.org_id,
        AutomationRule.is_active == True
    ).all()

    norm_pin = pin.upper()
    try:
        val_float = float(new_value)
    except (ValueError, TypeError):
        val_float = None

    for rule in rules:
        cond_str = rule.trigger_config.get("condition", rule.name)
        should_trigger = False

        # Robust regex matching: "When Temperature (V2) > 30 °C" or "V2 > 30"
        match = re.search(r'(V\d+)\)?\s*([><!=]=?)\s*([0-9.]+)', cond_str)
        if match:
            rule_pin, op, thresh_str = match.groups()
            rule_pin = rule_pin.upper()
            thresh = float(thresh_str)

            if rule_pin == norm_pin and val_float is not None:
                if op == ">" and val_float > thresh:
                    should_trigger = True
                elif op == ">=" and val_float >= thresh:
                    should_trigger = True
                elif op == "<" and val_float < thresh:
                    should_trigger = True
                elif op == "<=" and val_float <= thresh:
                    should_trigger = True
                elif op in ("==", "=") and abs(val_float - thresh) < 0.001:
                    should_trigger = True
                elif op == "!=" and abs(val_float - thresh) >= 0.001:
                    should_trigger = True
        
        # Check alarm state == 1
        elif "Alarm State (V6)" in cond_str or "V6" in cond_str:
            if norm_pin == "V6" and str(new_value).strip() in ("1", "true", "True"):
                should_trigger = True

        if should_trigger:
            act_str = rule.action_config.get("action", "")
            action_desc = act_str or rule.action_type

            # Action 1: Turn Fan Relay (V3) ON / Pin actuation
            pin_act_match = re.search(r'(V\d+)\s*(ON|OFF|\d+)', action_desc, re.IGNORECASE)
            if "Fan Relay" in action_desc or "V3" in action_desc or pin_act_match:
                target_pin = "V3"
                target_val = "1"
                if pin_act_match:
                    target_pin = pin_act_match.group(1).upper()
                    token = pin_act_match.group(2).upper()
                    target_val = "1" if token in ("ON", "1") else "0"
                elif "OFF" in action_desc.upper():
                    target_val = "0"

                # Update datastream in DB
                ds = db.query(Datastream).filter(
                    Datastream.template_id == device.template_id,
                    Datastream.pin == target_pin
                ).first()
                if ds:
                    ds.current_value = target_val
                    db.commit()

                    # Save telemetry point
                    try:
                        t_pt = TelemetryTimeSeries(
                            device_id=device.id,
                            pin=target_pin,
                            value=float(target_val)
                        )
                        db.add(t_pt)
                        db.commit()
                    except Exception:
                        pass

                    triggered_actions.append({
                        "rule": rule.name,
                        "action": f"Wrote {target_val} to {target_pin}",
                        "targetPin": target_pin,
                        "targetValue": target_val
                    })

                    # Broadcast live WebSocket event if hub provided
                    if hub:
                        import asyncio
                        try:
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                asyncio.ensure_future(hub.broadcast_event("onValueUpdated", {
                                    "deviceId": device.id,
                                    "stream": target_pin,
                                    "value": target_val
                                }))
                        except Exception as e:
                            logger.warning(f"Failed to broadcast rule event: {e}")

            # Action 2: Notifications / Terminal Log
            if "Alert Notification" in action_desc or "Terminal" in action_desc:
                alert_msg = f"[AUTOMATION] Rule '{rule.name}' triggered by {norm_pin}={new_value}!"
                term_ds = db.query(Datastream).filter(
                    Datastream.template_id == device.template_id,
                    Datastream.pin == "V7"
                ).first()
                if term_ds:
                    term_ds.current_value = alert_msg
                    db.commit()
                    if hub:
                        import asyncio
                        try:
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                asyncio.ensure_future(hub.broadcast_event("onValueUpdated", {
                                    "deviceId": device.id,
                                    "stream": "V7",
                                    "value": alert_msg
                                }))
                        except Exception:
                            pass

                triggered_actions.append({
                    "rule": rule.name,
                    "action": "Notification Dispatched",
                    "message": alert_msg
                })

    return triggered_actions
