from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from datetime import datetime
from backend.database import get_db
from backend.models.entities import Device, Datastream, DashboardWidget, TelemetryTimeSeries
from backend.websocket_hub import hub
from backend.rules_engine import evaluate_rules_for_device

router = APIRouter(prefix="/api/v1/app", tags=["mobile-app"])

@router.get("/devices")
def get_mobile_devices(db: Session = Depends(get_db)):
    """Mobile App endpoint returning device list with live summary pins"""
    devices = db.query(Device).all()
    results = []
    for d in devices:
        datastreams = db.query(Datastream).filter(Datastream.template_id == d.template_id).all()
        ds_map = {ds.pin: ds.current_value for ds in datastreams}
        results.append({
            "id": d.id,
            "name": d.name,
            "status": d.status,
            "hardware": d.template.hardware_mcu if d.template else "ESP32",
            "connectionType": d.template.connection_type if d.template else "WI_FI",
            "authToken": d.auth_token,
            "firmwareVersion": d.firmware_version,
            "summaryValues": {
                "button": ds_map.get("V0", "0"),
                "slider": ds_map.get("V1", "128"),
                "temperature": ds_map.get("V2", "25.0"),
                "relay": ds_map.get("V3", "0"),
                "humidity": ds_map.get("V5", "50")
            }
        })
    return results

@router.get("/devices/{device_id}/dashboard")
def get_mobile_dashboard(device_id: int, db: Session = Depends(get_db)):
    """Mobile App dashboard layout and live values"""
    d = db.query(Device).filter(Device.id == device_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Device not found")

    datastreams = db.query(Datastream).filter(Datastream.template_id == d.template_id).all()
    widgets = db.query(DashboardWidget).filter(DashboardWidget.template_id == d.template_id).all()

    ds_dict = {
        ds.pin: {
            "name": ds.name,
            "dataType": ds.data_type,
            "min": ds.min_value,
            "max": ds.max_value,
            "units": ds.units,
            "value": ds.current_value
        }
        for ds in datastreams
    }

    widget_list = []
    for w in widgets:
        val = ds_dict.get(w.pin, {}).get("value", "0")
        widget_list.append({
            "id": w.id,
            "widgetType": w.widget_type,
            "label": w.label,
            "pin": w.pin,
            "color": w.on_color or "#10f17f",
            "settings": w.settings,
            "currentValue": val
        })

    return {
        "device": {
            "id": d.id,
            "name": d.name,
            "status": d.status,
            "hardware": d.template.hardware_mcu if d.template else "ESP32",
            "authToken": d.auth_token
        },
        "datastreams": ds_dict,
        "widgets": widget_list
    }

@router.post("/devices/{device_id}/write")
async def write_mobile_pin(device_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    """Actuate hardware or set virtual pin directly from the Mobile App"""
    d = db.query(Device).filter(Device.id == device_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Device not found")

    stream = payload.get("stream", "").upper()
    val = str(payload.get("value", ""))

    ds = db.query(Datastream).filter(
        Datastream.template_id == d.template_id,
        Datastream.pin == stream
    ).first()

    if ds:
        ds.current_value = val
        num_val = None
        try:
            num_val = float(val)
        except ValueError:
            pass

        point = TelemetryTimeSeries(
            device_id=d.id,
            pin=stream,
            value=val,
            numeric_value=num_val,
            timestamp=datetime.utcnow()
        )
        db.add(point)
        d.last_reported_at = datetime.utcnow()
        db.commit()

        # 1. Trigger automations engine
        try:
            evaluate_rules_for_device(db, d.id, stream, val, hub=hub)
        except Exception:
            pass

        # 2. Broadcast to Web Console and all other clients in REAL-TIME!
        await hub.broadcast_event("onValueUpdated", {
            "deviceId": device_id,
            "stream": stream,
            "value": val,
            "source": "MOBILE_APP",
            "timestamp": datetime.utcnow().isoformat()
        })

    return {"status": "ok", "pin": stream, "value": val}

@router.get("/devices/{device_id}/telemetry")
def get_device_telemetry(device_id: int, pin: str = "V2", limit: int = 50, db: Session = Depends(get_db)):
    """Fetch time-series telemetry records for SuperChart and historical analytics"""
    d = db.query(Device).filter(Device.id == device_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Device not found")

    points = db.query(TelemetryTimeSeries).filter(
        TelemetryTimeSeries.device_id == device_id,
        TelemetryTimeSeries.pin == pin.upper()
    ).order_by(TelemetryTimeSeries.timestamp.desc()).limit(limit).all()

    points.reverse() # chronological order for charts
    return [
        {
            "timestamp": p.timestamp.isoformat(),
            "pin": p.pin,
            "value": p.value,
            "numericValue": p.numeric_value or (float(p.value) if p.value and p.value.replace('.', '', 1).isdigit() else 0.0)
        }
        for p in points
    ]

@router.post("/devices/{device_id}/batch_write")
async def batch_write_pins(device_id: int, payload: list = Body(...), db: Session = Depends(get_db)):
    """Actuate multiple pins simultaneously (e.g. Joystick X and Y axes)"""
    d = db.query(Device).filter(Device.id == device_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Device not found")

    updated = []
    for item in payload:
        stream = str(item.get("stream", "")).upper()
        val = str(item.get("value", ""))
        ds = db.query(Datastream).filter(
            Datastream.template_id == d.template_id,
            Datastream.pin == stream
        ).first()

        if ds:
            ds.current_value = val
            num_val = None
            try:
                num_val = float(val)
            except ValueError:
                pass

            point = TelemetryTimeSeries(
                device_id=d.id,
                pin=stream,
                value=val,
                numeric_value=num_val,
                timestamp=datetime.utcnow()
            )
            db.add(point)
            updated.append({"stream": stream, "value": val})

            await hub.broadcast_event("onValueUpdated", {
                "deviceId": device_id,
                "stream": stream,
                "value": val,
                "source": "MOBILE_APP",
                "timestamp": datetime.utcnow().isoformat()
            })

    d.last_reported_at = datetime.utcnow()
    db.commit()
    return {"status": "ok", "updated": updated}

@router.post("/devices/{device_id}/widgets")
def add_dashboard_widget(device_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    """Add a new widget to the device template from Widget Box Drawer"""
    d = db.query(Device).filter(Device.id == device_id).first()
    if not d or not d.template_id:
        raise HTTPException(status_code=404, detail="Device or template not found")

    widget_type = payload.get("widgetType", "BUTTON")
    label = payload.get("label", "New Widget")
    pin = payload.get("pin", "V0")

    widget = DashboardWidget(
        template_id=d.template_id,
        widget_type=widget_type,
        label=label,
        pin=pin,
        grid_x=payload.get("gridX", 0),
        grid_y=payload.get("gridY", 0),
        width=payload.get("width", 2),
        height=payload.get("height", 2),
        on_color="#10f17f",
        off_color="#2b2d30",
        settings=payload.get("settings", {})
    )
    db.add(widget)
    db.commit()
    db.refresh(widget)

    return {
        "status": "ok",
        "widget": {
            "id": widget.id,
            "widgetType": widget.widget_type,
            "label": widget.label,
            "pin": widget.pin,
            "settings": widget.settings
        }
    }

@router.delete("/devices/{device_id}/widgets/{widget_id}")
def delete_dashboard_widget(device_id: int, widget_id: int, db: Session = Depends(get_db)):
    """Delete a widget from the template layout"""
    w = db.query(DashboardWidget).filter(DashboardWidget.id == widget_id).first()
    if not w:
        raise HTTPException(status_code=404, detail="Widget not found")
    db.delete(w)
    db.commit()
    return {"status": "ok", "deletedWidgetId": widget_id}

