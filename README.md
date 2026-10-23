# Axon IoT

Axon IoT is a self-hosted Blynk-compatible IoT prototype with a FastAPI web console, mobile companion UI, SQLite persistence, WebSocket events, and a TCP hardware gateway.

## Local setup

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m playwright install chromium

export DATABASE_URL="sqlite:///$(pwd)/axon_iot.db"
export AXON_CORS_ORIGINS="http://127.0.0.1:8000,http://localhost:8000"
python run_server.py
```

Open `http://127.0.0.1:8000/` for the web console or `http://127.0.0.1:8000/app.html` for the mobile companion. The hardware gateway listens on TCP port `8080`.

For a clean development database, delete `axon_iot.db` before starting. Demo bootstrap records are created once for local evaluation; production deployments should load tenant data through an authenticated provisioning workflow.

## Verification

```bash
python tests/test_all_tabs_real_database.py
python test_no_mock_dynamic.py
python test_apk_fidelity.py
```

Set `AXON_FRONTEND_DIR` only when serving a separately deployed frontend directory. Never commit secrets or use the development seed token in production.

For a production deployment, enable API session enforcement and keep device
tokens redacted in list/dashboard responses:

```bash
export AXON_REQUIRE_AUTH=true
export AXON_EXPOSE_DEVICE_TOKENS=false
export AXON_SEED_PASSWORD="use-a-secret-bootstrap-password"
```

Create a session through `POST /api/v1/auth/login`, then send
`Authorization: Bearer <token>` to protected `/api/v1/*` routes. Device
external API calls continue to authenticate with their per-device token.
