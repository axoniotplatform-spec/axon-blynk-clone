"""
enterprise_rbac.py — Enterprise Team Invitations, Multi-Role RBAC Management,
Embedded Fleet Simulator Controls, and Scheduled/On-Demand Executive Telemetry Digests.
"""

import io
import csv
import secrets
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Body, Response
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.database import get_db
from backend.models.entities import (
    User, Organization, Device, Datastream, TelemetryTimeSeries, AnomalyAlert, AuditEvent
)
from backend.api import auth as auth_api
from backend.simulator_service import fleet_simulator
from backend.notification_service import dispatch_anomaly_notification
from backend.websocket_hub import hub

router = APIRouter(prefix="/api/v1", tags=["enterprise-rbac-sim-reports"])

VALID_ROLES = {"Superadmin", "Admin", "Operator", "Observer"}


# ==========================================
# 1. LIVE FLEET SIMULATOR CONTROLS (STEP 3)
# ==========================================
@router.get("/simulator/status")
def get_simulator_status():
    return fleet_simulator.status()


@router.post("/simulator/start")
async def start_simulator(payload: dict = Body(default={})):
    interval = float(payload.get("interval_sec", 2.0))
    st = fleet_simulator.start(interval_sec=interval)
    await hub.broadcast_event("onSimulatorStateChanged", st)
    return st


@router.post("/simulator/stop")
async def stop_simulator():
    st = await fleet_simulator.stop()
    await hub.broadcast_event("onSimulatorStateChanged", st)
    return st


# ==========================================
# 2. TEAM INVITES & RBAC PERMISSIONS (STEP 4)
# ==========================================
@router.get("/team/members")
def list_team_members(db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.id.asc()).all()
    return [
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role,
            "orgId": u.org_id,
            "status": getattr(u, "status", "Active") or "Active",
            "createdAt": u.created_at.strftime("%Y-%m-%d") if getattr(u, "created_at", None) else "Active",
        }
        for u in users
    ]


@router.post("/team/invite")
async def invite_team_member(payload: dict = Body(...), db: Session = Depends(get_db)):
    email = payload.get("email", "").strip().lower()
    name = payload.get("name", "").strip() or (email.split("@")[0].title() if email else "Field Engineer")
    role = payload.get("role", "Operator").strip()
    if role not in VALID_ROLES:
        role = "Operator"
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid work email is required")

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        existing.role = role
        db.commit()
        return {
            "status": "updated_existing",
            "member": {"id": existing.id, "name": existing.name, "email": existing.email, "role": existing.role},
        }

    org = db.query(Organization).first()
    org_id = org.id if org else 1
    temp_password = payload.get("temp_password", "").strip() or ("Axon-" + secrets.token_hex(4))

    user = User(
        org_id=org_id,
        email=email,
        name=name,
        role=role,
        password_hash=auth_api.hash_password(temp_password),
    )
    db.add(user)
    db.add(AuditEvent(
        org_id=org_id,
        actor_email="admin@axon-iot.internal",
        action="TEAM_MEMBER_INVITED",
        resource_type="user",
        resource_id=email,
        details={"role": role, "name": name},
    ))
    db.commit()
    db.refresh(user)

    member_info = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "temporaryPassword": temp_password,
    }
    await hub.broadcast_event("onTeamMemberInvited", member_info)
    return {"status": "invited", "member": member_info}


@router.patch("/team/members/{user_id}/role")
async def update_member_role(user_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    role = payload.get("role", "").strip()
    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Role must be one of {sorted(VALID_ROLES)}")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Team member not found")

    old_role = user.role
    user.role = role
    db.add(AuditEvent(
        org_id=user.org_id or 1,
        actor_email="admin@axon-iot.internal",
        action="RBAC_ROLE_CHANGED",
        resource_type="user",
        resource_id=str(user.id),
        details={"email": user.email, "from": old_role, "to": role},
    ))
    db.commit()
    await hub.broadcast_event("onMemberRoleUpdated", {"userId": user.id, "role": role})
    return {"status": "updated", "userId": user.id, "role": role}


# ==========================================
# 3. EXECUTIVE TELEMETRY DIGEST REPORTS (STEP 4)
# ==========================================
def _build_digest_summary(db: Session) -> dict:
    total_devices = db.query(Device).count()
    online_devices = db.query(Device).filter(Device.status == "ONLINE").count()
    total_points = db.query(TelemetryTimeSeries).count()
    unresolved_anomalies = db.query(AnomalyAlert).filter(AnomalyAlert.is_resolved == False).count()
    resolved_anomalies = db.query(AnomalyAlert).filter(AnomalyAlert.is_resolved == True).count()
    total_users = db.query(User).count()

    pin_stats = []
    agg_rows = (
        db.query(
            TelemetryTimeSeries.pin,
            func.count(TelemetryTimeSeries.id),
            func.min(TelemetryTimeSeries.numeric_value),
            func.avg(TelemetryTimeSeries.numeric_value),
            func.max(TelemetryTimeSeries.numeric_value),
        )
        .group_by(TelemetryTimeSeries.pin)
        .all()
    )
    ds_map = {ds.pin: ds for ds in db.query(Datastream).all()}
    for pin, cnt, vmin, vavg, vmax in agg_rows:
        ds = ds_map.get(pin)
        pin_stats.append({
            "pin": pin,
            "name": ds.name if ds else pin,
            "units": ds.units if ds else "",
            "samples": cnt,
            "min": round(vmin, 2) if vmin is not None else None,
            "avg": round(vavg, 2) if vavg is not None else None,
            "max": round(vmax, 2) if vmax is not None else None,
            "current": ds.current_value if ds else None,
        })

    return {
        "generatedAt": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "fleet": {
            "totalDevices": total_devices,
            "onlineDevices": online_devices,
            "teamMembers": total_users,
            "simulatorRunning": fleet_simulator.status()["running"],
        },
        "telemetry": {
            "totalSamplesStored": total_points,
            "pinAggregates": pin_stats,
        },
        "reliability": {
            "unresolvedAnomalies": unresolved_anomalies,
            "resolvedAnomalies": resolved_anomalies,
        },
    }


@router.get("/reports/digest")
def get_executive_digest(db: Session = Depends(get_db)):
    return _build_digest_summary(db)


@router.get("/reports/digest.csv")
def download_executive_digest_csv(db: Session = Depends(get_db)):
    digest = _build_digest_summary(db)
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["Axon IoT Executive Telemetry Digest", digest["generatedAt"]])
    writer.writerow([
        "Total Devices", digest["fleet"]["totalDevices"],
        "Online Devices", digest["fleet"]["onlineDevices"],
        "Total Samples", digest["telemetry"]["totalSamplesStored"],
        "Open Anomalies", digest["reliability"]["unresolvedAnomalies"],
    ])
    writer.writerow([])
    writer.writerow(["Pin", "Datastream Name", "Samples", "Min", "Avg", "Max", "Latest Value", "Units"])
    for p in digest["telemetry"]["pinAggregates"]:
        writer.writerow([p["pin"], p["name"], p["samples"], p["min"], p["avg"], p["max"], p["current"], p["units"]])

    return Response(
        content=out.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=axon_executive_digest.csv"},
    )


@router.post("/reports/dispatch-digest")
async def dispatch_executive_digest(db: Session = Depends(get_db)):
    digest = _build_digest_summary(db)
    msg = (
        f"Executive Digest ({digest['generatedAt']}): "
        f"Devices={digest['fleet']['onlineDevices']}/{digest['fleet']['totalDevices']} online, "
        f"Samples={digest['telemetry']['totalSamplesStored']}, "
        f"Open Anomalies={digest['reliability']['unresolvedAnomalies']}."
    )
    from backend import notification_service
    notification_service._last_dispatch.pop("1_0_EXECUTIVE_DIGEST", None)
    res = dispatch_anomaly_notification(
        db=db,
        device_id=1,
        anomaly_type="EXECUTIVE_DIGEST",
        severity="INFO",
        message=msg,
        pin=0,
        value=float(digest["telemetry"]["totalSamplesStored"]),
    )
    db.add(AuditEvent(
        org_id=1,
        actor_email="admin@axon-iot.internal",
        action="DIGEST_REPORT_DISPATCHED",
        resource_type="report",
        resource_id="executive_digest",
        details={"samples": digest["telemetry"]["totalSamplesStored"]},
    ))
    db.commit()
    await hub.broadcast_event("onDigestDispatched", {"summary": msg})
    return {"status": "dispatched", "summary": msg, "channels": res}
