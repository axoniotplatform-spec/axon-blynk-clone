from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from typing import Optional
from backend.database import get_db
from backend.models.entities import Device, Datastream, TelemetryTimeSeries
from backend.rules_engine import evaluate_rules_for_device
from backend.websocket_hub import hub

from backend.hardware_gateway import hardware_gateway

router = APIRouter(prefix="/external/api", tags=["external_blynk_api"])

@router.get("/update")
@router.post("/update")
async def blynk_external_update(request: Request, token: str, db: Session = Depends(get_db)):
    """
    Standard Blynk External API:
    GET /external/api/update?token=xxx&V0=1&V1=250
    """
    device = db.query(Device).filter(Device.auth_token == token).first()
    if not device:
        raise HTTPException(status_code=400, detail="Invalid token")

    query_params = dict(request.query_params)
    updated_streams = {}

    for k, v in query_params.items():
        if k.lower() == "token":
            continue
        pin_name = k.upper()
        ds = db.query(Datastream).filter(
            Datastream.template_id == device.template_id,
            Datastream.pin == pin_name
        ).first()

        if ds:
            ds.current_value = str(v)
            db.commit()

            # Record time series point
            try:
                num_val = float(v)
                t_pt = TelemetryTimeSeries(device_id=device.id, pin=pin_name, value=num_val)
                db.add(t_pt)
                db.commit()
            except Exception:
                pass

            updated_streams[pin_name] = v

            # Broadcast live WebSocket event to web console
            await hub.broadcast_event("onValueUpdated", {
                "deviceId": device.id,
                "stream": pin_name,
                "value": v
            })

            # Evaluate automation rules
            evaluate_rules_for_device(db, device.id, pin_name, v, hub=hub)

    return Response(content="OK", media_type="text/plain")

@router.get("/get")
async def blynk_external_get(token: str, pin: Optional[str] = None, request: Request = None, db: Session = Depends(get_db)):
    """
    Standard Blynk External API:
    GET /external/api/get?token=xxx&pin=V0 or GET /external/api/get?token=xxx&v0
    Returns scalar plain text string.
    """
    device = db.query(Device).filter(Device.auth_token == token).first()
    if not device:
        raise HTTPException(status_code=400, detail="Invalid token")

    target_pin = pin
    if not target_pin and request:
        for k in request.query_params.keys():
            if k.lower() != "token":
                target_pin = k
                break

    if not target_pin:
        raise HTTPException(status_code=400, detail="Missing pin parameter")

    target_pin = target_pin.upper()
    ds = db.query(Datastream).filter(
        Datastream.template_id == device.template_id,
        Datastream.pin == target_pin
    ).first()

    if not ds:
        raise HTTPException(status_code=404, detail=f"Pin {target_pin} not found")

    return Response(content=str(ds.current_value or "0"), media_type="text/plain")

@router.get("/get/pins")
async def blynk_external_get_all_pins(token: str, db: Session = Depends(get_db)):
    """
    Standard Blynk External API:
    GET /external/api/get/pins?token=xxx
    Returns JSON dictionary of all virtual pin values: {"V0": "1", "V1": "128", ...}
    """
    device = db.query(Device).filter(Device.auth_token == token).first()
    if not device:
        raise HTTPException(status_code=400, detail="Invalid token")

    datastreams = db.query(Datastream).filter(Datastream.template_id == device.template_id).all()
    return {ds.pin: ds.current_value or "0" for ds in datastreams}

@router.get("/isHardwareConnected")
async def blynk_is_hardware_connected(token: str, db: Session = Depends(get_db)):
    """
    GET /external/api/isHardwareConnected?token=xxx
    Returns "true" or "false" based on live TCP socket and heartbeat
    """
    device = db.query(Device).filter(Device.auth_token == token).first()
    if not device:
        return Response(content="false", media_type="text/plain")

    is_online = (device.auth_token in hardware_gateway.connected_devices) or (device.status == "ONLINE")
    return Response(content="true" if is_online else "false", media_type="text/plain")

@router.get("/batch/update")
@router.post("/batch/update")
async def blynk_batch_update(request: Request, token: str, db: Session = Depends(get_db)):
    """
    Standard Blynk External API:
    GET /external/api/batch/update?token=xxx&V0=1&V1=200
    POST /external/api/batch/update?token=xxx with JSON body {"V0": "1", "V1": "200"}
    """
    device = db.query(Device).filter(Device.auth_token == token).first()
    if not device:
        raise HTTPException(status_code=400, detail="Invalid token")

    updates = {}
    if request.method == "POST":
        try:
            body = await request.json()
            if isinstance(body, dict):
                updates = body
        except Exception:
            pass

    # Merge query params
    for k, v in request.query_params.items():
        if k.lower() != "token":
            updates[k.upper()] = v

    for pin_name, val in updates.items():
        pin_upper = pin_name.upper()
        ds = db.query(Datastream).filter(
            Datastream.template_id == device.template_id,
            Datastream.pin == pin_upper
        ).first()

        if ds:
            ds.current_value = str(val)
            try:
                t_pt = TelemetryTimeSeries(device_id=device.id, pin=pin_upper, value=str(val), numeric_value=float(val))
                db.add(t_pt)
            except Exception:
                pass

            await hub.broadcast_event("onValueUpdated", {
                "deviceId": device.id,
                "stream": pin_upper,
                "value": str(val)
            })
            evaluate_rules_for_device(db, device.id, pin_upper, str(val), hub=hub)

    db.commit()
    return Response(content="OK", media_type="text/plain")

@router.get("/ota/check")
async def blynk_air_ota_check(token: str, current_version: str = "1.0.0", db: Session = Depends(get_db)):
    """
    Blynk.Air OTA (Over-The-Air) Firmware Update Check:
    GET /external/api/ota/check?token=xxx&current_version=1.0.0
    """
    device = db.query(Device).filter(Device.auth_token == token).first()
    if not device:
        raise HTTPException(status_code=400, detail="Invalid token")

    target_ver = device.firmware_version or "1.0.0"
    has_update = target_ver != current_version

    return {
        "status": "ok",
        "hasUpdate": has_update,
        "targetVersion": target_ver,
        "currentVersion": current_version,
        "hardware": device.template.hardware_mcu if device.template else "ESP32",
        "firmwareUrl": f"/firmware/binaries/{device.template_id}/latest.bin" if has_update else None
    }
