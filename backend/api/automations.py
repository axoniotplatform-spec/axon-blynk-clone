from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from backend.database import get_db
from backend.models.entities import AutomationRule, Organization

router = APIRouter(prefix="/api/v1/automations", tags=["automations"])

class AutomationCreate(BaseModel):
    name: str
    trigger_type: str = "DATASTREAM_VALUE"
    trigger_condition: str  # e.g. "When Temperature (V2) > 30 °C"
    action_type: str = "WRITE_PIN"
    action_desc: str        # e.g. "Turn Fan Relay (V3) ON"
    is_active: bool = True

@router.get("")
def list_automations(db: Session = Depends(get_db)):
    rules = db.query(AutomationRule).order_by(AutomationRule.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "triggerType": r.trigger_type,
            "condition": r.trigger_config.get("condition", r.name),
            "actionType": r.action_type,
            "action": r.action_config.get("action", r.action_type),
            "isActive": r.is_active,
            "createdAt": r.created_at.strftime("%b %d, %Y %I:%M %p")
        }
        for r in rules
    ]

@router.post("")
def create_automation(data: AutomationCreate, db: Session = Depends(get_db)):
    org = db.query(Organization).first()
    if not org:
        org = Organization(name="Default Organization", plan_tier="FREE")
        db.add(org)
        db.commit()
        db.refresh(org)

    rule = AutomationRule(
        org_id=org.id,
        name=data.name,
        trigger_type=data.trigger_type,
        trigger_config={"condition": data.trigger_condition},
        action_type=data.action_type,
        action_config={"action": data.action_desc},
        is_active=data.is_active
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return {"status": "created", "id": rule.id, "name": rule.name}

@router.delete("/{rule_id}")
def delete_automation(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(AutomationRule).filter(AutomationRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(rule)
    db.commit()
    return {"status": "deleted", "id": rule_id}

@router.patch("/{rule_id}/toggle")
def toggle_automation(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(AutomationRule).filter(AutomationRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    rule.is_active = not rule.is_active
    db.commit()
    return {"status": "updated", "id": rule.id, "isActive": rule.is_active}
