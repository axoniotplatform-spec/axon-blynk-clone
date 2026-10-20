from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from backend.database import get_db
from backend.models.entities import Device, Datastream, DashboardWidget, DeviceTemplate, TelemetryTimeSeries
from backend.websocket_hub import hub

router = APIRouter(prefix="/api/v1/devices", tags=["devices"])

@router.get("")
def list_devices(db: Session = Depends(get_db)):
    devices = db.query(Device).all()
    return [
        {
            "id": d.id,
            "name": d.name,
            "authToken": d.auth_token,
            "status": d.status,
            "templateId": d.template.template_id if d.template else None,
            "templateName": d.template.name if d.template else None,
            "hardware": d.template.hardware_mcu if d.template else "ESP32",
            "connectionType": d.template.connection_type if d.template else "WI_FI",
            "firmwareVersion": d.firmware_version,
            "lastReportedAt": d.last_reported_at.isoformat() if d.last_reported_at else None
        }
        for d in devices
    ]

@router.get("/{device_id}")
def get_device(device_id: int, db: Session = Depends(get_db)):
    d = db.query(Device).filter(Device.id == device_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Device not found")
    return {
        "id": d.id,
        "name": d.name,
        "authToken": d.auth_token,
        "status": d.status,
        "templateId": d.template.template_id if d.template else None,
        "templateName": d.template.name if d.template else None,
        "hardware": d.template.hardware_mcu if d.template else "ESP32",
        "connectionType": d.template.connection_type if d.template else "WI_FI",
        "heartbeatInterval": d.heartbeat_interval,
        "firmwareVersion": d.firmware_version,
        "blynkLibraryVersion": d.blynk_library_version,
        "lastReportedAt": d.last_reported_at.isoformat() if d.last_reported_at else None
    }

@router.get("/{device_id}/datastreams")
def get_device_datastreams(device_id: int, db: Session = Depends(get_db)):
    d = db.query(Device).filter(Device.id == device_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Device not found")
    datastreams = db.query(Datastream).filter(Datastream.template_id == d.template_id).all()
    return [
        {
            "id": ds.id,
            "pin": ds.pin,
            "name": ds.name,
            "dataType": ds.data_type,
            "min": ds.min_value,
            "max": ds.max_value,
            "step": ds.step,
            "value": ds.current_value,
            "units": ds.units,
            "color": ds.color_hex,
            "aggregation": ds.aggregation
        }
        for ds in datastreams
    ]

@router.get("/{device_id}/widgets")
def get_device_widgets(device_id: int, db: Session = Depends(get_db)):
    d = db.query(Device).filter(Device.id == device_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Device not found")
    widgets = db.query(DashboardWidget).filter(DashboardWidget.template_id == d.template_id).all()
    datastreams = db.query(Datastream).filter(Datastream.template_id == d.template_id).all()
    ds_map = {ds.pin: ds.current_value for ds in datastreams}

    return [
        {
            "id": w.id,
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
    ]

@router.get("/{device_id}/update")
async def update_pin_via_get(device_id: int, request: Request, db: Session = Depends(get_db)):
    """Blynk Hardware HTTP REST API: GET /api/v1/devices/{id}/update?V0=1"""
    d = db.query(Device).filter(Device.id == device_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Device not found")
    
    updates = {}
    params = dict(request.query_params)
    for pin_name, val in params.items():
        pin_upper = pin_name.upper()
        ds = db.query(Datastream).filter(
            Datastream.template_id == d.template_id,
            Datastream.pin == pin_upper
        ).first()
        if ds:
            ds.current_value = str(val)
            num_val = None
            try:
                num_val = float(val)
            except ValueError:
                pass

            point = TelemetryTimeSeries(
                device_id=d.id,
                pin=pin_upper,
                value=str(val),
                numeric_value=num_val,
                timestamp=datetime.utcnow()
            )
            db.add(point)
            updates[pin_upper] = str(val)

            # Broadcast real-time update
            await hub.broadcast_event("onValueUpdated", {
                "deviceId": device_id,
                "stream": pin_upper,
                "value": str(val),
                "timestamp": datetime.utcnow().isoformat()
            })

    db.commit()
    return {"status": "ok", "updated": updates}

@router.get("/{device_id}/get")
def get_pin_value(device_id: int, pin: str = Query(..., alias="pin"), db: Session = Depends(get_db)):
    """Blynk Hardware HTTP REST API: GET /api/v1/devices/{id}/get?pin=V0"""
    d = db.query(Device).filter(Device.id == device_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Device not found")
    
    ds = db.query(Datastream).filter(
        Datastream.template_id == d.template_id,
        Datastream.pin == pin.upper()
    ).first()
    if not ds:
        raise HTTPException(status_code=404, detail=f"Pin {pin} not found on device")
    
    return {"pin": ds.pin, "value": ds.current_value}
