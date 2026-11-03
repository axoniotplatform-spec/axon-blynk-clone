from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from backend.database import get_db
from backend.models.entities import AnomalyAlert, AuditEvent, Device
from backend.notification_service import get_channel_status, dispatch_anomaly_notification

router = APIRouter(prefix="/api/v1", tags=["anomalies_and_audit"])

@router.get("/anomalies/events")
@router.get("/anomalies")
def list_anomaly_alerts(
    device_id: Optional[int] = None,
    unresolved_only: bool = False,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    query = db.query(AnomalyAlert)
    if device_id:
        query = query.filter(AnomalyAlert.device_id == device_id)
    if unresolved_only:
        query = query.filter(AnomalyAlert.is_resolved == False)
    alerts = query.order_by(AnomalyAlert.created_at.desc()).limit(limit).all()
    
    return [
        {
            "id": a.id,
            "deviceId": a.device_id,
            "anomalyType": a.anomaly_type,
            "severity": a.severity,
            "message": a.message,
            "pin": a.pin,
            "value": a.value,
            "isResolved": a.is_resolved,
            "createdAt": a.created_at.isoformat() if a.created_at else None
        }
        for a in alerts
    ]

@router.post("/anomalies/{alert_id}/resolve")
def resolve_anomaly_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(AnomalyAlert).filter(AnomalyAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Anomaly alert not found")
    alert.is_resolved = True
    db.commit()
    return {"status": "success", "message": f"Alert {alert_id} resolved"}

@router.get("/enterprise/audit-log")
@router.get("/audit")
def list_audit_events(
    limit: int = Query(50, ge=1, le=200),
    action: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(AuditEvent)
    if action:
        query = query.filter(AuditEvent.action == action)
    events = query.order_by(AuditEvent.created_at.desc()).limit(limit).all()

    return [
        {
            "id": e.id,
            "orgId": e.org_id,
            "userId": e.user_id,
            "actorEmail": e.actor_email,
            "action": e.action,
            "resourceType": e.resource_type,
            "resourceId": e.resource_id,
            "details": e.details,
            "ipAddress": e.ip_address,
            "createdAt": e.created_at.isoformat() if e.created_at else None
        }
        for e in events
    ]

@router.post("/audit/log")
def create_audit_event(payload: dict, db: Session = Depends(get_db)):
    actor = payload.get("actorEmail", "admin@axon-iot.internal")
    action = payload.get("action", "SYSTEM_ACTION")
    evt = AuditEvent(
        org_id=payload.get("orgId", 1),
        user_id=payload.get("userId"),
        actor_email=actor,
        action=action,
        resource_type=payload.get("resourceType"),
        resource_id=str(payload.get("resourceId", "")),
        details=payload.get("details", {}),
        ip_address=payload.get("ipAddress", "127.0.0.1")
    )
    db.add(evt)
    db.commit()
    return {"status": "success", "eventId": evt.id}

@router.get("/notifications/status")
def notification_channels_status():
    return get_channel_status()

@router.post("/notifications/test")
def send_test_notification(payload: dict = None, db: Session = Depends(get_db)):
    payload = payload or {}
    device_id = payload.get("deviceId", 1)
    message = payload.get("message", "Manual test alert triggered from Axon Console")
    res = dispatch_anomaly_notification(
        db=db,
        device_id=device_id,
        anomaly_type="MANUAL_TEST_ALERT",
        severity="INFO",
        message=message,
        pin=payload.get("pin", 2),
        value=payload.get("value", 30.0)
    )
    return {"status": "success", "dispatch_result": res}
