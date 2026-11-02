"""
health.py — Axon IoT Production Health & Readiness Check Endpoint
Provides deep operational telemetry for Docker, Kubernetes, Render, and uptime monitors.
"""

import time
import os
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.database import get_db
from backend.models.entities import Device, Datastream

router = APIRouter(prefix="/api/v1", tags=["health"])

_start_time = time.time()

@router.get("/health")
@router.get("/healthz")
def health_check(db: Session = Depends(get_db)):
    """
    Returns system health status, database connectivity, and device counts.
    """
    uptime_sec = int(time.time() - _start_time)
    
    # 1. Check Database Connectivity
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    # 2. Query Device Metrics
    try:
        total_devices = db.query(Device).count()
        online_devices = db.query(Device).filter(Device.is_online == True).count()
    except Exception:
        total_devices = 0
        online_devices = 0

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "service": "Axon-Blynk Clone Platform",
        "version": "2.2.0-enterprise",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": uptime_sec,
        "database": {
            "status": db_status,
            "engine": "sqlite" if "sqlite" in os.getenv("DATABASE_URL", "sqlite") else "postgresql"
        },
        "gateways": {
            "http_port": int(os.getenv("PORT", "8000")),
            "blynk_tcp_port": int(os.getenv("AXON_HARDWARE_PORT", "8080")),
            "binary_wire_protocol": "blynk_v1"
        },
        "metrics": {
            "total_devices": total_devices,
            "online_devices": online_devices
        }
    }
