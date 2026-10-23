import os
from typing import Optional


def expose_device_token(token: Optional[str]) -> Optional[str]:
    """Return a token only when explicitly enabled; otherwise return a safe preview."""
    if token is None:
        return None
    if os.getenv("AXON_EXPOSE_DEVICE_TOKENS", "false").lower() in {"1", "true", "yes"}:
        return token
    if len(token) <= 8:
        return "••••"
    return f"{token[:4]}••••{token[-4:]}"
