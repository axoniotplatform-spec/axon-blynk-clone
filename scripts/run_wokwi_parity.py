#!/usr/bin/env python3
"""Build and run the Axon ESP32/Blynk hardware parity test in Wokwi."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT_SOURCE = ROOT / "wokwi"
TOKEN_MARKER = "__AXON_TEST_DEVICE_TOKEN__"
REQUIRED_SERIAL_MARKERS = (
    "WIFI_CONNECTED",
    "BLYNK_CONNECTED",
    "V2_TELEMETRY_SENT",
    "WOKWI_PARITY_PASS",
)
TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9._-]{12,128}$")


def fail(message: str, code: int = 1) -> "NoReturn":
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(code)


def safe_output(text: str, token: str) -> str:
    """Defensively redact a supplied credential from any child-process output."""
    return text.replace(token, "[REDACTED]") if token else text


def run(command: list[str], *, cwd: Path, env: dict[str, str], token: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    output = safe_output(result.stdout or "", token)
    if output.strip():
        print(output.rstrip())
    if result.returncode:
        fail(f"Command failed with exit code {result.returncode}: {Path(command[0]).name}")
    return result


def main() -> int:
    token = os.environ.get("AXON_TEST_DEVICE_TOKEN", "").strip()
    if not token:
        fail("Set AXON_TEST_DEVICE_TOKEN to the auth token of an authorized test device.")
    if not TOKEN_PATTERN.fullmatch(token):
        fail("AXON_TEST_DEVICE_TOKEN contains unsupported characters or has an unexpected length.")

    wokwi_token = os.environ.get("WOKWI_CLI_TOKEN", "").strip()
    if not wokwi_token:
        fail("Set WOKWI_CLI_TOKEN in the environment; do not pass it as a command-line argument.")
    if len(wokwi_token) != 44 or not wokwi_token.startswith("wok_"):
        fail("WOKWI_CLI_TOKEN must use the documented Wokwi format (44 characters beginning with 'wok_').")

    pio = shutil.which("pio")
    pio_command = [pio] if pio else [sys.executable, "-m", "platformio"]
    wokwi_cli = shutil.which("wokwi-cli")
    if not wokwi_cli and (Path.home() / "bin" / "wokwi-cli").is_file():
        wokwi_cli = str(Path.home() / "bin" / "wokwi-cli")
    if not wokwi_cli:
        fail("Wokwi CLI 'wokwi-cli' is not installed or not on PATH.")
    if not (PROJECT_SOURCE / "platformio.ini").is_file():
        fail(f"Missing PlatformIO project: {PROJECT_SOURCE / 'platformio.ini'}")

    env = os.environ.copy()
    # Keep the CI token in the child environment only; never write it to project files.
    env["WOKWI_CLI_TOKEN"] = wokwi_token

    with tempfile.TemporaryDirectory(prefix="axon-wokwi-parity-") as temp_dir:
        project = Path(temp_dir) / "project"
        shutil.copytree(PROJECT_SOURCE, project)

        sketch = project / "src" / "main.cpp"
        source = sketch.read_text(encoding="utf-8")
        if source.count(TOKEN_MARKER) != 1:
            fail("The firmware template must contain exactly one token injection marker.")
        # JSON string escaping produces a valid C++ string literal for the restricted alphabet.
        sketch.write_text(source.replace(TOKEN_MARKER, json.dumps(token)), encoding="utf-8")

        print("Building temporary ESP32 project with official Blynk library 1.4.0...")
        run([*pio_command, "run", "--project-dir", str(project)], cwd=project, env=env, token=token)

        serial_log = project / "serial.log"
        print("Starting Wokwi simulation; the clone TCP gateway must be reachable on port 8080...")
        run(
            [
                wokwi_cli,
                "--timeout",
                "90000",
                "--expect-text",
                "WOKWI_PARITY_PASS",
                "--serial-log-file",
                str(serial_log),
                str(project),
            ],
            cwd=project,
            env=env,
            token=token,
        )

        log_text = serial_log.read_text(encoding="utf-8", errors="replace") if serial_log.exists() else ""
        missing = [marker for marker in REQUIRED_SERIAL_MARKERS if marker not in log_text]
        if missing:
            # The serial log may contain protocol/library output; redact before displaying it.
            excerpt = safe_output(log_text[-3000:], token)
            if excerpt:
                print("--- sanitized serial log tail ---", file=sys.stderr)
                print(excerpt, file=sys.stderr)
            fail("Missing expected serial assertion(s): " + ", ".join(missing))

    print("PASS: Wi-Fi, Blynk login, and V2 telemetry serial assertions all passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
