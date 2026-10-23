from fastapi import APIRouter, Depends, HTTPException, Body, Response, Form, File, UploadFile
from sqlalchemy.orm import Session
from datetime import datetime
import io
import csv
import secrets
from typing import List, Optional
from backend.database import get_db
from backend.models.entities import (
    LocationSite, DeviceSnapshot, InAppBroadcast, StaticToken,
    WebhookSubscription, MathRule, OAuthApp, CustomDashboard,
    Device, Datastream, DeviceTemplate, Organization, TelemetryTimeSeries
)
from backend.websocket_hub import hub
from backend.security import expose_device_token

router = APIRouter(prefix="/api/v1", tags=["platform-operations"])

# ==========================================
# 1. LOCATIONS API
# ==========================================
@router.get("/locations")
def list_locations(db: Session = Depends(get_db)):
    locs = db.query(LocationSite).all()
    if not locs:
        # Seed default locations if empty
        l1 = LocationSite(name="Factory Floor Alpha", address="Primary manufacturing facility and IoT cluster", status="Operational", device_count=1, latitude=6.5244, longitude=3.3792)
        l2 = LocationSite(name="Greenhouse West", address="Automated irrigation & soil telemetry site", status="Provisioning", device_count=1, latitude=6.4531, longitude=3.4215)
        db.add(l1)
        db.add(l2)
        db.commit()
        locs = [l1, l2]
    return [
        {
            "id": l.id,
            "name": l.name,
            "address": l.address,
            "status": l.status,
            "deviceCount": l.device_count,
            "latitude": l.latitude,
            "longitude": l.longitude,
            "createdAt": l.created_at.strftime("%b %d, %Y")
        }
        for l in locs
    ]

@router.post("/locations")
async def create_location(payload: dict = Body(...), db: Session = Depends(get_db)):
    name = payload.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Location name is required")
    
    loc = LocationSite(
        name=name,
        address=payload.get("address", "Deployed Site"),
        status=payload.get("status", "Operational"),
        device_count=int(payload.get("device_count", 1)),
        latitude=float(payload.get("latitude", 6.5244)),
        longitude=float(payload.get("longitude", 3.3792))
    )
    db.add(loc)
    db.commit()
    db.refresh(loc)

    # Broadcast event
    await hub.broadcast_event("onLocationCreated", {"id": loc.id, "name": loc.name})
    return {"status": "success", "location": {"id": loc.id, "name": loc.name, "address": loc.address, "status": loc.status, "deviceCount": loc.device_count}}

@router.delete("/locations/{loc_id}")
def delete_location(loc_id: int, db: Session = Depends(get_db)):
    loc = db.query(LocationSite).filter(LocationSite.id == loc_id).first()
    if loc:
        db.delete(loc)
        db.commit()
    return {"status": "deleted"}

# ==========================================
# 2. DEVICE SNAPSHOTS API
# ==========================================
@router.get("/snapshots")
def list_snapshots(db: Session = Depends(get_db)):
    snaps = db.query(DeviceSnapshot).order_by(DeviceSnapshot.created_at.desc()).all()
    if not snaps:
        # Seed baseline snapshot
        s1 = DeviceSnapshot(
            name="Snapshot #001 - Production Baseline",
            description="Captured live state: 13 Datastreams Recorded",
            state_data={"devices": 1, "datastreams": 13, "mode": "STABLE"},
            size_kb=142
        )
        db.add(s1)
        db.commit()
        snaps = [s1]
    return [
        {
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "sizeKb": s.size_kb,
            "createdAt": s.created_at.strftime("%b %d, %Y %H:%M:%S")
        }
        for s in snaps
    ]

@router.post("/snapshots")
async def take_snapshot(payload: dict = Body(default={}), db: Session = Depends(get_db)):
    devices = db.query(Device).all()
    datastreams = db.query(Datastream).all()
    
    count = db.query(DeviceSnapshot).count() + 1
    snap_name = payload.get("name", f"Snapshot #{count:03d} - State Capture")
    
    state_dump = {
        "timestamp": datetime.utcnow().isoformat(),
        "devices": [{"id": d.id, "name": d.name, "status": d.status} for d in devices],
        "datastreams": [{"pin": ds.pin, "val": ds.current_value} for ds in datastreams]
    }
    
    snap = DeviceSnapshot(
        name=snap_name,
        description=f"Captured {len(devices)} Devices & {len(datastreams)} Datastreams",
        state_data=state_dump,
        size_kb=130 + (len(datastreams) * 4)
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)

    await hub.broadcast_event("onSnapshotCreated", {"id": snap.id, "name": snap.name})
    return {"status": "success", "snapshot": {"id": snap.id, "name": snap.name, "description": snap.description, "createdAt": snap.created_at.strftime("%b %d, %Y %H:%M:%S")}}

@router.post("/snapshots/{snap_id}/restore")
async def restore_snapshot(snap_id: int, db: Session = Depends(get_db)):
    snap = db.query(DeviceSnapshot).filter(DeviceSnapshot.id == snap_id).first()
    if not snap:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    # Restore datastream values
    if snap.state_data and "datastreams" in snap.state_data:
        for item in snap.state_data["datastreams"]:
            ds = db.query(Datastream).filter(Datastream.pin == item["pin"]).first()
            if ds:
                ds.current_value = str(item["val"])
        db.commit()
        await hub.broadcast_event("onStateRestored", {"snapshotId": snap.id, "name": snap.name})

    return {"status": "restored", "name": snap.name}

# ==========================================
# 3. IN-APP MESSAGING & BROADCASTS API
# ==========================================
@router.get("/broadcasts")
def list_broadcasts(db: Session = Depends(get_db)):
    msgs = db.query(InAppBroadcast).order_by(InAppBroadcast.created_at.desc()).all()
    if not msgs:
        b1 = InAppBroadcast(
            title="[HIGH TEMP ALERT] Temperature crossed 30°C threshold",
            message="Dispatched to all administrators via Push & WebSocket. Action: Fan Relay engaged.",
            severity="ALERT",
            target_audience="Admins"
        )
        db.add(b1)
        db.commit()
        msgs = [b1]
    return [
        {
            "id": m.id,
            "title": m.title,
            "message": m.message,
            "severity": m.severity,
            "targetAudience": m.target_audience,
            "createdAt": m.created_at.strftime("%b %d, %Y %H:%M")
        }
        for m in msgs
    ]

@router.post("/broadcasts")
async def send_broadcast(payload: dict = Body(...), db: Session = Depends(get_db)):
    title = payload.get("title", "").strip()
    msg = payload.get("message", "").strip()
    if not title or not msg:
        raise HTTPException(status_code=400, detail="Title and message are required")

    broadcast = InAppBroadcast(
        title=title,
        message=msg,
        severity=payload.get("severity", "INFO"),
        target_audience=payload.get("target_audience", "All Users")
    )
    db.add(broadcast)
    db.commit()
    db.refresh(broadcast)

    # Broadcast in real time over WebSocket to all connected Web Consoles and Mobile Apps!
    await hub.broadcast_event("onBroadcastMessage", {
        "id": broadcast.id,
        "title": broadcast.title,
        "message": broadcast.message,
        "severity": broadcast.severity
    })

    return {"status": "success", "broadcast": {"id": broadcast.id, "title": broadcast.title, "message": broadcast.message, "createdAt": broadcast.created_at.strftime("%b %d, %Y %H:%M")}}

# ==========================================
# 4. ORGANIZATIONS API
# ==========================================
@router.get("/organizations")
def list_organizations(db: Session = Depends(get_db)):
    orgs = db.query(Organization).all()
    return [
        {
            "id": o.id,
            "name": o.name,
            "plan_tier": o.plan_tier,
            "region": o.server_region,
            "device_count": len(o.devices) if hasattr(o, 'devices') else 0,
            "user_count": len(o.users) if hasattr(o, 'users') else 0,
            "created_at": o.created_at.strftime("%b %d, %Y")
        }
        for o in orgs
    ]

@router.post("/organizations")
def create_organization(payload: dict = Body(...), db: Session = Depends(get_db)):
    name = payload.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Organization name required")
    
    org = Organization(
        name=name,
        plan_tier=payload.get("plan_tier", "free"),
        server_region=payload.get("region", "global")
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return {"status": "created", "organization": {"id": org.id, "name": org.name, "plan_tier": org.plan_tier}}

@router.delete("/organizations/{org_id}")
def delete_organization(org_id: int, db: Session = Depends(get_db)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    db.delete(org)
    db.commit()
    return {"status": "deleted"}

# ==========================================
# 5. CUSTOM DASHBOARDS API
# ==========================================
@router.get("/dashboards")
def list_dashboards(db: Session = Depends(get_db)):
    dashboards = db.query(CustomDashboard).all()
    if not dashboards:
        d1 = CustomDashboard(slug="blinking-led", title="BLINKING LED", description="ESP32 Blinking LED Controller")
        d2 = CustomDashboard(slug="smart-greenhouse", title="Smart Greenhouse", description="Automated irrigation & environmental control")
        db.add(d1)
        db.add(d2)
        db.commit()
        dashboards = [d1, d2]
    return [{"id": d.id, "slug": d.slug, "title": d.title, "description": d.description} for d in dashboards]

@router.post("/dashboards")
def create_dashboard(payload: dict = Body(...), db: Session = Depends(get_db)):
    title = payload.get("title", "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="Dashboard title is required")
    slug = title.lower().replace(" ", "-").replace("/", "-")
    
    dash = CustomDashboard(
        slug=slug,
        title=title,
        description=payload.get("description", "Custom Blynk Dashboard")
    )
    db.add(dash)
    db.commit()
    db.refresh(dash)
    return {"status": "created", "dashboard": {"id": dash.id, "slug": dash.slug, "title": dash.title}}

# ==========================================
# 6. DEVELOPER ZONE (STATIC TOKENS, WEBHOOKS, RULES, OAUTH)
# ==========================================
@router.get("/devzone/static-tokens")
def get_static_tokens(db: Session = Depends(get_db)):
    toks = db.query(StaticToken).all()
    if not toks:
        dev = db.query(Device).first()
        t1 = StaticToken(device_id=dev.id if dev else 1, token_id="TOK-STATIC-001", token_value=dev.auth_token if dev else "yhdHK6Vuj2F6X7CUnX-QQIpuEl9Yy_dk", expiration="Never (Permanent)")
        db.add(t1)
        db.commit()
        toks = [t1]
    return [{"id": t.id, "tokenId": t.token_id, "tokenValue": expose_device_token(t.token_value), "expiration": t.expiration, "isActive": t.is_active} for t in toks]

@router.post("/devzone/static-tokens")
def create_static_token(payload: dict = Body(...), db: Session = Depends(get_db)):
    token_val = secrets.token_urlsafe(24).replace("-", "").replace("_", "")[:32]
    count = db.query(StaticToken).count() + 1
    t = StaticToken(
        token_id=f"TOK-STATIC-{count:03d}",
        token_value=token_val,
        expiration=payload.get("expiration", "Never (Permanent)")
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return {"status": "created", "token": {"tokenId": t.token_id, "tokenValue": t.token_value, "expiration": t.expiration}}

@router.get("/devzone/webhooks")
def get_webhooks(db: Session = Depends(get_db)):
    whs = db.query(WebhookSubscription).all()
    if not whs:
        w1 = WebhookSubscription(name="Discord High-Temp Dispatcher", trigger_pin="V2 (> 30°C)", endpoint_url="https://discord.com/api/webhooks/axon-alerts", http_method="POST")
        db.add(w1)
        db.commit()
        whs = [w1]
    return [{"id": w.id, "name": w.name, "triggerPin": w.trigger_pin, "url": w.endpoint_url, "method": w.http_method, "isActive": w.is_active} for w in whs]

@router.post("/devzone/webhooks")
def create_webhook(payload: dict = Body(...), db: Session = Depends(get_db)):
    name = payload.get("name", "").strip()
    url = payload.get("url", "").strip()
    if not name or not url:
        raise HTTPException(status_code=400, detail="Name and URL are required")
    wh = WebhookSubscription(name=name, trigger_pin=payload.get("trigger_pin", "V2"), endpoint_url=url, http_method=payload.get("method", "POST"))
    db.add(wh)
    db.commit()
    db.refresh(wh)
    return {"status": "created", "webhook": {"id": wh.id, "name": wh.name, "triggerPin": wh.trigger_pin, "url": wh.endpoint_url}}

@router.get("/devzone/rules")
def get_math_rules(db: Session = Depends(get_db)):
    rules = db.query(MathRule).all()
    if not rules:
        r1 = MathRule(name="Celsius to Fahrenheit", input_stream="V2", expression="(x * 9/5) + 32", output_stream="V12")
        db.add(r1)
        db.commit()
        rules = [r1]
    return [{"id": r.id, "name": r.name, "input_pin": r.input_stream, "expression": r.expression, "output_pin": r.output_stream, "enabled": r.is_active} for r in rules]

@router.post("/devzone/rules")
def create_math_rule(payload: dict = Body(...), db: Session = Depends(get_db)):
    name = payload.get("name", "").strip()
    expr = payload.get("expression", "").strip()
    if not name or not expr:
        raise HTTPException(status_code=400, detail="Rule name and expression required")
    rule = MathRule(
        name=name,
        input_stream=payload.get("input_pin", payload.get("input", "V2")),
        expression=expr,
        output_stream=payload.get("output_pin", payload.get("output", "V12"))
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return {"status": "created", "rule": {"id": rule.id, "name": rule.name, "input_pin": rule.input_stream, "expression": rule.expression, "output_pin": rule.output_stream}}

# ==========================================
# 6b. OAUTH 2.0 CLIENTS
# ==========================================
@router.get("/devzone/oauth")
def list_oauth_apps(db: Session = Depends(get_db)):
    apps = db.query(OAuthApp).all()
    return [{"id": a.id, "client_name": a.client_name, "client_id": a.client_id, "redirect_uri": a.redirect_uris, "scopes": a.scopes} for a in apps]

@router.post("/devzone/oauth")
def register_oauth_app(payload: dict = Body(...), db: Session = Depends(get_db)):
    name = payload.get("client_name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Client name required")
    client_id  = "axon_" + secrets.token_urlsafe(12).replace("-","").replace("_","")[:16]
    client_sec = secrets.token_urlsafe(32)
    app = OAuthApp(
        client_name=name,
        client_id=client_id,
        client_secret=client_sec,
        redirect_uris=payload.get("redirect_uri", "https://localhost/callback"),
        scopes=",".join(payload.get("scopes", ["read:devices"]))
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return {"status": "created", "client_id": app.client_id, "client_secret": app.client_secret, "name": app.client_name}

# ==========================================
# 6c. ASSET UPLOAD (stored as metadata)
# ==========================================
@router.post("/devzone/assets")
async def upload_asset(name: str = Form(...), asset_type: str = Form("other"), file: UploadFile = File(None)):
    """Stores asset metadata. In production, file would go to S3/GCS/local storage."""
    import os
    asset_dir = os.path.join(os.path.dirname(__file__), "..", "..", "assets")
    os.makedirs(asset_dir, exist_ok=True)
    saved_path = None
    if file:
        safe_name = name.replace(" ", "_")
        saved_path = os.path.join(asset_dir, safe_name)
        content = await file.read()
        with open(saved_path, "wb") as f:
            f.write(content)
    return {"status": "uploaded", "name": name, "asset_type": asset_type, "path": saved_path or f"assets/{name}"}

# ==========================================
# 7. REAL CUSTOM DATA CSV EXPORT
# ==========================================
@router.get("/custom-data/export.csv")
def export_telemetry_csv(db: Session = Depends(get_db)):
    """Generates and streams a real CSV containing telemetry time series from SQLite!"""
    rows = db.query(TelemetryTimeSeries).order_by(TelemetryTimeSeries.timestamp.desc()).limit(500).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Timestamp (UTC)", "Device ID", "Virtual Pin", "Value", "Numeric Value"])
    
    if not rows:
        # Include current active datastreams
        ds_list = db.query(Datastream).all()
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        for ds in ds_list:
            writer.writerow([now_str, 1, ds.pin, ds.current_value, ds.current_value])
    else:
        for r in rows:
            writer.writerow([r.timestamp.strftime("%Y-%m-%d %H:%M:%S"), r.device_id, r.pin, r.value, r.numeric_value or ""])

    output.seek(0)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=blynk_telemetry_export.csv"}
    )

@router.get("/custom-data/telemetry")
def get_custom_data_telemetry(db: Session = Depends(get_db)):
    rows = db.query(TelemetryTimeSeries).order_by(TelemetryTimeSeries.timestamp.desc()).limit(100).all()
    if not rows:
        ds_list = db.query(Datastream).all()
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        return [
            {
                "timestamp": now_str,
                "pin": ds.pin,
                "name": ds.name,
                "value": ds.current_value,
                "type": ds.data_type
            }
            for ds in ds_list
        ]
    return [
        {
            "timestamp": r.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "pin": r.pin,
            "value": r.value,
            "numericValue": r.numeric_value
        }
        for r in rows
    ]

# ==========================================
# 8. IOT AI ASSISTANT API ("Ask AI")
# ==========================================
@router.post("/ai/ask")
def ask_iot_ai(payload: dict = Body(...), db: Session = Depends(get_db)):
    query = payload.get("query", "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")
    
    # Query knowledge base & current platform context
    dev_count = db.query(Device).count()
    tmpl_count = db.query(DeviceTemplate).count()
    q_lower = query.lower()
    
    if "firmware" in q_lower or "code" in q_lower or "esp32" in q_lower:
        ans = f"To connect your ESP32, include <BlynkSimpleEsp32.h> and call Blynk.config(auth, '127.0.0.1', 8080). Currently, you have {dev_count} device(s) registered in your SQLite database."
    elif "token" in q_lower or "auth" in q_lower:
        dev = db.query(Device).first()
        tok = dev.auth_token if dev else "yhdHK6Vuj2F6X7CUnX-QQIpuEl9Yy_dk"
        ans = f"Your primary device auth token is `{tok}`. You can copy it directly from the Devices tab or Developer Zone -> Static Tokens."
    elif "rule" in q_lower or "automation" in q_lower:
        ans = "The Axon Rules Engine evaluates telemetry on every virtual pin write (e.g. V2 > 30°C triggers V3 Fan Relay). You can configure logic under Automations or Developer Zone -> Rule Engine."
    else:
        ans = f"Blynk IoT AI Assistant: Your system has {dev_count} devices and {tmpl_count} templates configured. All telemetry is streaming live over WebSocket and TCP Port 8080."

    return {
        "status": "success",
        "query": query,
        "answer": ans
    }
