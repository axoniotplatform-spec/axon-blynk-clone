"""Utilities for local test scripts. Tokens are read only from the configured test database."""

from pathlib import Path
import os
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

ARTIFACT_DIR = Path(os.environ.get("AXON_TEST_ARTIFACT_DIR", REPO_ROOT / "tests" / "artifacts"))
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


def get_seeded_device_credentials():
    """Return (id, auth_token, template_id, org_id) for the first test device."""
    from backend.database import SessionLocal
    from backend.models.entities import Device

    db = SessionLocal()
    try:
        device = db.query(Device).order_by(Device.id).first()
        if device is None:
            raise RuntimeError("No device is seeded in the configured test database")
        return device.id, device.auth_token, device.template_id, device.org_id
    finally:
        db.close()


def get_seeded_device_token():
    return get_seeded_device_credentials()[1]
