from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import secrets
from pydantic import BaseModel
from backend.database import get_db
from backend.models.entities import (
    Device, Datastream, DashboardWidget, DeviceTemplate, TelemetryTimeSeries, Organization
)
from backend.websocket_hub import hub
from backend.security import expose_device_token
from backend.api import auth as auth_api


class DeviceCreate(BaseModel):
    name: str
    template_id: Optional[int] = None
    hardware_mcu: Optional[str] = "ESP32"
    connection_type: Optional[str] = "WI_FI"
    org_id: Optional[int] = 1


class WidgetCreate(BaseModel):
    widget_type: str = "SWITCH"
    label: str
    pin: str = "V8"
    min_value: float = 0.0
    max_value: float = 100.0
    units: str = ""


def enforce_write_rbac(request: Request):
    """Blocks hardware actuator mutations when user or simulated role is Read-Only Observer."""
    sim_role = request.headers.get("x-axon-role", "").strip().lower()
    if sim_role in ("observer", "read-only", "readonly", "viewer"):
        raise HTTPException(status_code=403, detail="Observer role is read-only: hardware actuator writes are locked.")

    auth_hdr = request.headers.get("authorization", "")
    if auth_hdr.startswith("Bearer "):
        tok = auth_hdr.removeprefix("Bearer ").strip()
        sess = auth_api.SESSION_TOKENS.get(tok)
        if isinstance(sess, dict) and str(sess.get("role", "")).lower() in ("observer", "viewer", "read-only"):
            raise HTTPException(status_code=403, detail="Observer role is read-only: hardware actuator writes are locked.")


router = APIRouter(prefix="/api/v1/devices", tags=["devices"])


@router.post("")
async def create_device(payload: DeviceCreate, db: Session = Depends(get_db)):
    tmpl = None
    if payload.template_id:
        tmpl = db.query(DeviceTemplate).filter(DeviceTemplate.id == payload.template_id).first()

    if not tmpl:
        hw = (payload.hardware_mcu or "ESP32").upper()
        tmpl = db.query(DeviceTemplate).filter(DeviceTemplate.hardware_mcu == hw).first()

    if not tmpl:
        tmpl = db.query(DeviceTemplate).first()

    if not tmpl:
        org = db.query(Organization).first()
        org_id = org.id if org else 1
        tid = "TMPL" + secrets.token_hex(4).upper()
        tmpl = DeviceTemplate(
            org_id=org_id,
            template_id=tid,
            name=f"{payload.hardware_mcu or 'ESP32'} Industrial Template",
            hardware_mcu=(payload.hardware_mcu or "ESP32").upper(),
            connection_type=(payload.connection_type or "WI_FI").upper(),
            description="Auto-provisioned template from Axon Mobile Developer Mode",
        )
        db.add(tmpl)
        db.commit()
        db.refresh(tmpl)

    token = secrets.token_urlsafe(24).replace("-", "").replace("_", "")[:32]
    while len(token) < 32:
        token += secrets.token_hex(4)
    token = token[:32]

    dev = Device(
        org_id=payload.org_id or tmpl.org_id,
        template_id=tmpl.id,
        name=payload.name.strip() or "Axon Field Node",
        auth_token=token,
        status="OFFLINE",
        firmware_version="1.0.0",
        blynk_library_version="1.3.5",
        last_reported_at=None,
        last_connected_at=None,
    )
    db.add(dev)
    db.commit()
    db.refresh(dev)

    res = {
        "id": dev.id,
        "name": dev.name,
        "authToken": dev.auth_token,
        "token": dev.auth_token,
        "status": dev.status,
        "templateId": tmpl.template_id,
        "templateName": tmpl.name,
        "hardware": tmpl.hardware_mcu,
        "connectionType": tmpl.connection_type,
        "firmwareVersion": dev.firmware_version,
    }
    await hub.broadcast_event("onDeviceCreated", res)
    return res


@router.delete("/{device_id}")
async def delete_device(device_id: int, request: Request, db: Session = Depends(get_db)):
    enforce_write_rbac(request)
    d = db.query(Device).filter(Device.id == device_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Device not found")
    db.delete(d)
    db.commit()
    await hub.broadcast_event("onDeviceDeleted", {"id": device_id})
    return {"status": "deleted", "id": device_id}


@router.get("")
def list_devices(db: Session = Depends(get_db)):
    devices = db.query(Device).all()
    return [
        {
            "id": d.id,
            "name": d.name,
            "authToken": expose_device_token(d.auth_token),
            "status": d.status,
            "templateId": d.template.template_id if d.template else None,
            "templateName": d.template.name if d.template else None,
            "hardware": d.template.hardware_mcu if d.template else "ESP32",
            "connectionType": d.template.connection_type if d.template else "WI_FI",
            "firmwareVersion": d.firmware_version,
            "lastReportedAt": d.last_reported_at.isoformat() if d.last_reported_at else None,
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
        "authToken": expose_device_token(d.auth_token),
        "status": d.status,
        "templateId": d.template.template_id if d.template else None,
        "templateName": d.template.name if d.template else None,
        "hardware": d.template.hardware_mcu if d.template else "ESP32",
        "connectionType": d.template.connection_type if d.template else "WI_FI",
        "heartbeatInterval": d.heartbeat_interval,
        "firmwareVersion": d.firmware_version,
        "blynkLibraryVersion": d.blynk_library_version,
        "lastReportedAt": d.last_reported_at.isoformat() if d.last_reported_at else None,
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
            "aggregation": ds.aggregation,
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
            "settings": w.settings,
        }
        for w in widgets
    ]


@router.post("/{device_id}/widgets")
async def create_device_widget(
    device_id: int,
    payload: WidgetCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    enforce_write_rbac(request)
    d = db.query(Device).filter(Device.id == device_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Device not found")

    pin_clean = payload.pin.strip().upper()
    if not pin_clean.startswith("V"):
        pin_clean = f"V{pin_clean}"

    ds = db.query(Datastream).filter(
        Datastream.template_id == d.template_id,
        Datastream.pin == pin_clean,
    ).first()
    if not ds:
        wtype = payload.widget_type.upper()
        dtype = "INTEGER" if wtype in ("SWITCH", "WEB_STYLED_BUTTON", "LED") else "DOUBLE"
        ds = Datastream(
            template_id=d.template_id,
            pin=pin_clean,
            name=payload.label.strip(),
            data_type=dtype,
            pin_type="VIRTUAL",
            min_value=payload.min_value,
            max_value=payload.max_value,
            step=1.0,
            default_value="0",
            current_value="0",
            units=payload.units,
            color_hex="#00E5FF",
        )
        db.add(ds)
        db.commit()
        db.refresh(ds)

    existing_count = db.query(DashboardWidget).filter(DashboardWidget.template_id == d.template_id).count()
    w = DashboardWidget(
        template_id=d.template_id,
        widget_type=payload.widget_type.upper(),
        label=payload.label.strip(),
        pin=pin_clean,
        grid_x=(existing_count * 4) % 12,
        grid_y=12 + (existing_count // 3) * 2,
        width=4,
        height=2,
        settings={
            "min": payload.min_value,
            "max": payload.max_value,
            "units": payload.units,
            "customMobile": True,
        },
    )
    db.add(w)
    db.commit()
    db.refresh(w)

    created = {
        "id": w.id,
        "widgetType": w.widget_type,
        "label": w.label,
        "pin": w.pin,
        "currentValue": ds.current_value or "0",
        "settings": w.settings,
    }
    await hub.broadcast_event("onWidgetCreated", {"deviceId": d.id, "widget": created})
    return created


@router.delete("/{device_id}/widgets/{widget_id}")
async def delete_device_widget(
    device_id: int,
    widget_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    enforce_write_rbac(request)
    w = db.query(DashboardWidget).filter(DashboardWidget.id == widget_id).first()
    if not w:
        raise HTTPException(status_code=404, detail="Widget not found")
    db.delete(w)
    db.commit()
    await hub.broadcast_event("onWidgetDeleted", {"deviceId": device_id, "widgetId": widget_id})
    return {"status": "deleted", "widgetId": widget_id}


@router.get("/{device_id}/update")
async def update_pin_via_get(device_id: int, request: Request, db: Session = Depends(get_db)):
    """Blynk Hardware HTTP REST API: GET /api/v1/devices/{id}/update?V0=1"""
    enforce_write_rbac(request)
    d = db.query(Device).filter(Device.id == device_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Device not found")

    updates = {}
    params = dict(request.query_params)
    for pin_name, val in params.items():
        pin_upper = pin_name.upper()
        ds = db.query(Datastream).filter(
            Datastream.template_id == d.template_id,
            Datastream.pin == pin_upper,
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
                timestamp=datetime.utcnow(),
            )
            db.add(point)
            updates[pin_upper] = str(val)

            await hub.broadcast_event("onValueUpdated", {
                "deviceId": device_id,
                "stream": pin_upper,
                "value": str(val),
                "timestamp": datetime.utcnow().isoformat(),
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
        Datastream.pin == pin.upper(),
    ).first()
    if not ds:
        raise HTTPException(status_code=404, detail=f"Pin {pin} not found on device")

    return {"pin": ds.pin, "value": ds.current_value}
