"""
ota.py — Axon IoT Enterprise Mobile Pairing, QR Code Provisioning, Blynk.Air OTA Firmware Push,
and Live Notification Channel Configurator.
"""

import os
import json
import socket
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form, Body, Query
from fastapi.responses import Response, FileResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.entities import Device, AnomalyAlert, WebhookSubscription
from backend.notification_service import get_channel_status, dispatch_anomaly_notification
from backend.websocket_hub import hub
from backend.qr_svg import render_qr_svg

router = APIRouter(tags=["ota-and-connect"])

OTA_STORAGE_DIR = Path(__file__).resolve().parent.parent.parent / "firmware" / "ota_releases"
OTA_MANIFEST_FILE = OTA_STORAGE_DIR / "manifest.json"


def _detect_lan_ip() -> str:
    override = os.getenv("AXON_PUBLIC_HOST", "").strip()
    if override:
        return override
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(0.5)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            if ip and not ip.startswith("127."):
                return ip
    except Exception:
        pass
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if ip and not ip.startswith("127.") and not ip.startswith("169.254."):
                return ip
    except Exception:
        pass
    return "127.0.0.1"


def _load_ota_manifest() -> list:
    OTA_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    if OTA_MANIFEST_FILE.is_file():
        try:
            return json.loads(OTA_MANIFEST_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_ota_manifest(entries: list) -> None:
    OTA_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    OTA_MANIFEST_FILE.write_text(json.dumps(entries, indent=2), encoding="utf-8")


# ==========================================
# 1. AUTO-LAN-IP DISCOVERY & QR PAIRING
# ==========================================
@router.get("/api/v1/system/connect-info")
def get_system_connect_info(request: Request):
    lan_ip = _detect_lan_ip()
    http_port = int(os.getenv("PORT", "8000"))
    hw_port = int(os.getenv("AXON_HARDWARE_PORT", "8080"))

    scheme = request.headers.get("x-forwarded-proto", request.url.scheme or "http")
    req_host = request.headers.get("host", f"{lan_ip}:{http_port}")
    if req_host.startswith(("127.0.0.1", "localhost")):
        gateway_base = f"{scheme}://{lan_ip}:{http_port}"
    else:
        gateway_base = f"{scheme}://{req_host}"

    apk_dir = Path(__file__).resolve().parent.parent.parent / "mobile_flutter" / "build" / "app" / "outputs" / "flutter-apk"
    local_apk = None
    for cand in ("app-arm64-v8a-release.apk", "app-release.apk", "app-armeabi-v7a-release.apk"):
        p = apk_dir / cand
        if p.is_file():
            local_apk = p
            break

    cloud_apk_url = os.getenv(
        "AXON_APK_RELEASE_URL",
        "https://github.com/axoniotplatform-spec/axon-blynk-clone/releases/download/latest-apk/Axon-IoT-Mobile-arm64-v8a.apk",
    )

    return {
        "lan_ip": lan_ip,
        "http_port": http_port,
        "hardware_tcp_port": hw_port,
        "gateway_base_url": gateway_base,
        "flutter_mobile_web_url": f"{gateway_base}/flutter/?server={gateway_base}",
        "lan_apk_download_url": f"{gateway_base}/downloads/axon-iot.apk",
        "cloud_apk_release_url": cloud_apk_url,
        "apk_local_ready": local_apk is not None,
        "apk_size_mb": round(local_apk.stat().st_size / (1024 * 1024), 2) if local_apk else 17.8,
        "apk_signed_release": (Path(__file__).resolve().parent.parent.parent / "mobile_flutter" / "android" / "key.properties").is_file(),
        "notification_channels": get_channel_status(),
    }


@router.get("/api/v1/system/qr.svg")
def generate_qr_code_svg(data: str = Query(..., min_length=1, max_length=260)):
    try:
        svg = render_qr_svg(data)
        return Response(content=svg, media_type="image/svg+xml", headers={"Cache-Control": "no-store"})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ==========================================
# 2. BLYNK.AIR COMPATIBLE OTA FIRMWARE PUSH
# ==========================================
@router.get("/api/v1/ota/releases")
def list_ota_releases():
    return _load_ota_manifest()


@router.post("/api/v1/ota/upload")
async def upload_ota_firmware(
    version: str = Form(...),
    hardware_mcu: str = Form("ESP32"),
    template_id: str = Form("ALL"),
    notes: str = Form("Over-the-air production firmware update"),
    file: Optional[UploadFile] = File(None),
):
    version_clean = version.strip().lstrip("vV")
    if not version_clean:
        raise HTTPException(status_code=400, detail="Firmware version is required")

    OTA_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    if file is not None:
        raw_bytes = await file.read()
        orig_name = file.filename or f"axon_{hardware_mcu.lower()}_{version_clean}.bin"
    else:
        # Generate deterministic ESP32 OTA diagnostic image header (0xE9 magic byte) for instant testing
        header = b"\xE9\x03\x02\x20" + f"AXON-OTA-FW:{hardware_mcu}:v{version_clean}:{datetime.utcnow().isoformat()}".encode("utf-8")
        raw_bytes = header.ljust(4096, b"\xFF")
        orig_name = f"axon_{hardware_mcu.lower()}_v{version_clean}.bin"

    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Uploaded firmware binary is empty")

    sha256_hex = hashlib.sha256(raw_bytes).hexdigest()
    md5_hex = hashlib.md5(raw_bytes).hexdigest()
    stored_filename = f"{hardware_mcu.lower()}_{version_clean}_{sha256_hex[:8]}.bin"
    bin_path = OTA_STORAGE_DIR / stored_filename
    bin_path.write_bytes(raw_bytes)

    manifest = _load_ota_manifest()
    entry = {
        "id": len(manifest) + 1,
        "version": version_clean,
        "hardware_mcu": hardware_mcu.upper(),
        "template_id": template_id,
        "filename": stored_filename,
        "original_name": orig_name,
        "size_bytes": len(raw_bytes),
        "sha256": sha256_hex,
        "md5": md5_hex,
        "notes": notes,
        "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
    }
    manifest.insert(0, entry)
    _save_ota_manifest(manifest)

    await hub.broadcast_event("onOtaReleasePublished", entry)
    return {"status": "published", "release": entry}


def _parse_semver(v: str):
    parts = []
    for p in (v or "0.0.0").strip().lstrip("vV").split("."):
        digits = "".join(ch for ch in p if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


@router.get("/external/api/ota/firmware")
async def hardware_ota_firmware_stream(
    request: Request,
    token: str = Query(...),
    version: Optional[str] = Query(None),
    mcu: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    device = db.query(Device).filter(Device.auth_token == token).first()
    if not device:
        raise HTTPException(status_code=401, detail="Invalid hardware auth token")

    current_ver = (
        version
        or request.headers.get("x-esp32-version")
        or request.headers.get("x-esp8266-version")
        or device.firmware_version
        or "1.0.0"
    )
    hw_mcu = (mcu or "ESP32").upper()

    manifest = _load_ota_manifest()
    candidates = [
        r for r in manifest
        if r.get("hardware_mcu", "ESP32") in (hw_mcu, "ALL")
    ]
    if not candidates:
        return Response(status_code=304)

    candidates.sort(key=lambda r: _parse_semver(r.get("version", "0.0.0")), reverse=True)
    latest = candidates[0]
    if _parse_semver(latest["version"]) <= _parse_semver(current_ver):
        return Response(status_code=304)

    bin_path = OTA_STORAGE_DIR / latest["filename"]
    if not bin_path.is_file():
        raise HTTPException(status_code=404, detail="Firmware binary missing on server")

    device.firmware_version = latest["version"]
    device.last_seen = datetime.utcnow()
    db.commit()

    await hub.broadcast_event("onDeviceOtaStarted", {
        "device_id": device.id,
        "device_name": device.name,
        "from_version": current_ver,
        "to_version": latest["version"],
    })

    return FileResponse(
        bin_path,
        media_type="application/octet-stream",
        filename=latest["filename"],
        headers={
            "x-MD5": latest["md5"],
            "X-Axon-SHA256": latest["sha256"],
            "X-Axon-Version": latest["version"],
        },
    )


# ==========================================
# 3. LIVE NOTIFICATION CHANNEL CONFIG & TEST
# ==========================================
@router.post("/api/v1/notifications/configure")
def configure_notification_channels(payload: dict = Body(...), db: Session = Depends(get_db)):
    tg_token = payload.get("telegram_bot_token", "").strip()
    tg_chat = payload.get("telegram_chat_id", "").strip()
    sms_url = payload.get("sms_gateway_url", "").strip()
    alert_phone = payload.get("alert_phone", "").strip()
    webhook_url = payload.get("webhook_url", "").strip()

    if tg_token:
        os.environ["AXON_TELEGRAM_BOT_TOKEN"] = tg_token
    if tg_chat:
        os.environ["AXON_TELEGRAM_CHAT_ID"] = tg_chat
    if sms_url:
        os.environ["AXON_SMS_GATEWAY_URL"] = sms_url
    if alert_phone:
        os.environ["AXON_ALERT_PHONE"] = alert_phone

    if webhook_url:
        existing = db.query(WebhookSubscription).filter(WebhookSubscription.endpoint_url == webhook_url).first()
        if not existing:
            db.add(WebhookSubscription(
                name="Operator Live Alert Webhook",
                trigger_pin="ALL_ANOMALIES",
                endpoint_url=webhook_url,
                http_method="POST",
                is_active=True,
            ))
            db.commit()

    return {"status": "configured", "channels": get_channel_status()}


@router.post("/api/v1/notifications/dispatch-test")
async def trigger_test_alert(payload: dict = Body(default={}), db: Session = Depends(get_db)):
    dev = db.query(Device).first()
    dev_id = dev.id if dev else 1
    msg = payload.get("message", "Operator diagnostic test alert triggered from Axon Console.")
    severity = payload.get("severity", "CRITICAL")

    alert = AnomalyAlert(
        device_id=dev_id,
        pin=2,
        anomaly_type="DIAGNOSTIC_TEST",
        severity=severity,
        message=msg,
        is_resolved=False,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    # Clear rate limit for DIAGNOSTIC_TEST so operator can test repeatedly
    from backend import notification_service
    notification_service._last_dispatch.pop(f"{dev_id}_2_DIAGNOSTIC_TEST", None)

    dispatch_res = dispatch_anomaly_notification(
        db=db,
        device_id=dev_id,
        anomaly_type="DIAGNOSTIC_TEST",
        severity=severity,
        message=msg,
        pin=2,
        value=99.9,
    )

    alert_dict = {
        "id": alert.id,
        "device_id": dev_id,
        "pin": "V2",
        "anomaly_type": alert.anomaly_type,
        "severity": alert.severity,
        "message": alert.message,
        "created_at": alert.created_at.isoformat(),
    }
    await hub.broadcast_event("ANOMALY_ALERT", alert_dict)
    return {"status": "dispatched", "alert": alert_dict, "dispatch": dispatch_res}
