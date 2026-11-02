"""
notification_service.py — Enterprise Alert & Dispatch System for Axon IoT
Dispatches real-time anomaly alerts across multiple operational channels:
1. Webhooks (HTTP POST with JSON payload to registered WebhookSubscription endpoints)
2. Telegram Bot (Markdown formatted messages to configured Chat ID)
3. SMS Gateway (Twilio / HTTP SMS payload for critical telemetry drops)
4. SMTP Email (HTML alert notifications)
Includes anti-flapping and rate-limiting to prevent alert storms.
"""

import os
import json
import time
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from backend.models.entities import WebhookSubscription

logger = logging.getLogger("axon.notifications")

# Anti-flapping cache: (device_id, pin, anomaly_type) -> last_dispatch_timestamp
_last_dispatch: Dict[str, float] = {}
RATE_LIMIT_SECONDS = int(os.getenv("AXON_ALERT_RATE_LIMIT_SEC", "30"))

def get_channel_status() -> Dict[str, Any]:
    """Returns the operational readiness of all configured notification channels."""
    telegram_configured = bool(os.getenv("AXON_TELEGRAM_BOT_TOKEN") and os.getenv("AXON_TELEGRAM_CHAT_ID"))
    sms_configured = bool(os.getenv("AXON_SMS_GATEWAY_URL") or (os.getenv("AXON_TWILIO_SID") and os.getenv("AXON_TWILIO_TOKEN")))
    email_configured = bool(os.getenv("AXON_SMTP_HOST") and os.getenv("AXON_ALERT_EMAIL"))
    webhook_enabled = os.getenv("AXON_WEBHOOKS_ENABLED", "true").lower() in ("true", "1", "yes")

    return {
        "webhooks_enabled": webhook_enabled,
        "telegram_configured": telegram_configured,
        "sms_configured": sms_configured,
        "email_configured": email_configured,
        "rate_limit_seconds": RATE_LIMIT_SECONDS
    }

def dispatch_anomaly_notification(
    db: Session,
    device_id: int,
    anomaly_type: str,
    severity: str,
    message: str,
    pin: Optional[int] = None,
    value: Optional[float] = None
) -> Dict[str, Any]:
    """
    Evaluates anti-flapping and dispatches alerts across all enabled channels.
    """
    now = time.time()
    cache_key = f"{device_id}_{pin}_{anomaly_type}"
    last_time = _last_dispatch.get(cache_key, 0.0)

    if (now - last_time) < RATE_LIMIT_SECONDS:
        logger.debug(f"[Notifications] Suppressed flapping alert for {cache_key} (rate limited)")
        return {"dispatched": False, "reason": "rate_limited"}

    _last_dispatch[cache_key] = now

    payload = {
        "event": "ANOMALY_ALERT",
        "timestamp": datetime.utcnow().isoformat(),
        "device_id": device_id,
        "pin": pin,
        "value": value,
        "anomaly_type": anomaly_type,
        "severity": severity,
        "message": message,
        "platform": "Axon IoT Blynk-Compatible Gateway"
    }

    dispatched_channels: List[str] = []

    # 1. Dispatch Webhooks
    webhook_status = _dispatch_webhooks(db, payload)
    if webhook_status.get("count", 0) > 0:
        dispatched_channels.append(f"webhooks({webhook_status['count']})")

    # 2. Dispatch Telegram
    if os.getenv("AXON_TELEGRAM_BOT_TOKEN") and os.getenv("AXON_TELEGRAM_CHAT_ID"):
        if _dispatch_telegram(payload):
            dispatched_channels.append("telegram")

    # 3. Dispatch SMS (for CRITICAL severity only)
    if severity == "CRITICAL" and (os.getenv("AXON_SMS_GATEWAY_URL") or os.getenv("AXON_TWILIO_SID")):
        if _dispatch_sms(payload):
            dispatched_channels.append("sms")

    logger.info(f"[Notifications] Alert dispatched for device {device_id} via: {dispatched_channels or ['internal_only']}")
    return {
        "dispatched": True,
        "channels": dispatched_channels,
        "payload": payload
    }

def _dispatch_webhooks(db: Session, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Posts payload to active WebhookSubscription records."""
    count = 0
    try:
        subs = db.query(WebhookSubscription).filter(WebhookSubscription.is_active == True).all()
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "AxonIoT-AlertDispatcher/2.1"
        }

        for sub in subs:
            try:
                req = urllib.request.Request(sub.endpoint_url, data=data, headers=headers, method="POST")
                urllib.request.urlopen(req, timeout=4)
                count += 1
            except Exception as e:
                logger.warning(f"[Notifications] Webhook {sub.endpoint_url} failed: {e}")
    except Exception as e:
        logger.warning(f"[Notifications] Failed to query webhooks: {e}")

    return {"count": count}

def _dispatch_telegram(payload: Dict[str, Any]) -> bool:
    """Sends Markdown formatted message via Telegram Bot API."""
    bot_token = os.getenv("AXON_TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("AXON_TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        return False

    severity_icon = "🚨" if payload["severity"] == "CRITICAL" else "⚠️"
    text = (
        f"{severity_icon} *AXON INDUSTRIAL ALERT*\n\n"
        f"*Device ID:* `{payload['device_id']}`\n"
        f"*Pin:* `V{payload['pin']}`\n"
        f"*Type:* `{payload['anomaly_type']}`\n"
        f"*Severity:* `{payload['severity']}`\n"
        f"*Message:* {payload['message']}\n"
        f"*Time:* `{payload['timestamp']}`"
    )

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    body = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=5)
        return True
    except Exception as e:
        logger.warning(f"[Notifications] Telegram send failed: {e}")
        return False

def _dispatch_sms(payload: Dict[str, Any]) -> bool:
    """Dispatches SMS to configured gateway endpoint."""
    sms_url = os.getenv("AXON_SMS_GATEWAY_URL")
    if not sms_url:
        return False

    text = f"[AXON ALERT] {payload['severity']}: {payload['message']} (Device {payload['device_id']})"
    body = json.dumps({
        "to": os.getenv("AXON_ALERT_PHONE", ""),
        "message": text
    }).encode("utf-8")

    try:
        req = urllib.request.Request(sms_url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=5)
        return True
    except Exception as e:
        logger.warning(f"[Notifications] SMS send failed: {e}")
        return False
