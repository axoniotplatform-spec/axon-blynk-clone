from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from backend.database import get_db
from backend.models.entities import DeviceTemplate, Datastream, DashboardWidget, Organization

router = APIRouter(prefix="/api/v1/templates", tags=["templates"])

class TemplateCreate(BaseModel):
    name: str
    template_id: str
    hardware_mcu: str = "ESP32"
    connection_type: str = "WI_FI"
    description: Optional[str] = ""

class DatastreamCreate(BaseModel):
    pin: str
    name: str
    data_type: str = "INTEGER"
    pin_type: str = "VIRTUAL"
    min_value: float = 0.0
    max_value: float = 1.0
    step: float = 1.0
    default_value: str = "0"
    units: Optional[str] = ""
    color_hex: str = "#0375de"

class WidgetCreate(BaseModel):
    widget_type: str
    label: str
    pin: str
    grid_x: int = 0
    grid_y: int = 0
    width: int = 4
    height: int = 2
    on_label: str = "ON"
    off_label: str = "OFF"
    on_color: str = "#0375de"
    off_color: str = "#fe0f00"
    on_back_color: str = "#0375de1a"
    off_back_color: str = "#fe0f001a"
    settings: Dict[str, Any] = {}

@router.get("")
def list_templates(db: Session = Depends(get_db)):
    templates = db.query(DeviceTemplate).all()
    return [
        {
            "id": t.id,
            "templateId": t.template_id,
            "name": t.name,
            "hardware": t.hardware_mcu,
            "connectionType": t.connection_type,
            "deviceCount": len(t.devices),
            "datastreamCount": len(t.datastreams),
            "widgetCount": len(t.widgets),
            "createdAt": t.created_at.isoformat()
        }
        for t in templates
    ]

@router.post("")
def create_template(data: TemplateCreate, db: Session = Depends(get_db)):
    org = db.query(Organization).first()
    if not org:
        org = Organization(name="Default Organization", plan_tier="FREE")
        db.add(org)
        db.commit()
        db.refresh(org)

    t = DeviceTemplate(
        org_id=org.id,
        template_id=data.template_id,
        name=data.name,
        hardware_mcu=data.hardware_mcu,
        connection_type=data.connection_type,
        description=data.description,
        firmware_config=f'#define BLYNK_TEMPLATE_ID "{data.template_id}"\n#define BLYNK_TEMPLATE_NAME "{data.name}"'
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return {"status": "created", "id": t.id, "templateId": t.template_id}

@router.get("/{template_id}")
def get_template(template_id: int, db: Session = Depends(get_db)):
    t = db.query(DeviceTemplate).filter(DeviceTemplate.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {
        "id": t.id,
        "templateId": t.template_id,
        "name": t.name,
        "hardware": t.hardware_mcu,
        "connectionType": t.connection_type,
        "description": t.description,
        "firmwareConfig": t.firmware_config,
        "datastreams": [
            {
                "id": ds.id,
                "pin": ds.pin,
                "name": ds.name,
                "dataType": ds.data_type,
                "min": ds.min_value,
                "max": ds.max_value,
                "step": ds.step,
                "units": ds.units,
                "color": ds.color_hex
            }
            for ds in t.datastreams
        ],
        "widgets": [
            {
                "id": w.id,
                "type": w.widget_type,
                "label": w.label,
                "pin": w.pin,
                "grid": {"x": w.grid_x, "y": w.grid_y, "w": w.width, "h": w.height},
                "onLabel": w.on_label,
                "offLabel": w.off_label,
                "onColor": w.on_color,
                "offColor": w.off_color
            }
            for w in t.widgets
        ]
    }

@router.post("/{template_id}/datastreams")
def add_datastream(template_id: int, data: DatastreamCreate, db: Session = Depends(get_db)):
    t = db.query(DeviceTemplate).filter(DeviceTemplate.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    
    ds = Datastream(
        template_id=t.id,
        pin=data.pin.upper(),
        name=data.name,
        data_type=data.data_type,
        pin_type=data.pin_type,
        min_value=data.min_value,
        max_value=data.max_value,
        step=data.step,
        default_value=data.default_value,
        units=data.units,
        color_hex=data.color_hex
    )
    db.add(ds)
    db.commit()
    db.refresh(ds)
    return {"status": "created", "id": ds.id, "pin": ds.pin}

@router.post("/{template_id}/widgets")
def add_widget(template_id: int, data: WidgetCreate, db: Session = Depends(get_db)):
    t = db.query(DeviceTemplate).filter(DeviceTemplate.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    
    w = DashboardWidget(
        template_id=t.id,
        widget_type=data.widget_type,
        label=data.label,
        pin=data.pin.upper(),
        grid_x=data.grid_x,
        grid_y=data.grid_y,
        width=data.width,
        height=data.height,
        on_label=data.on_label,
        off_label=data.off_label,
        on_color=data.on_color,
        off_color=data.off_color,
        on_back_color=data.on_back_color,
        off_back_color=data.off_back_color,
        settings=data.settings
    )
    db.add(w)
    db.commit()
    db.refresh(w)
    return {"status": "created", "id": w.id, "type": w.widget_type}
