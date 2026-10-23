import os
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from backend.database import engine, Base, SessionLocal
from backend.models.entities import Organization, User, DeviceTemplate, Device, Datastream, DashboardWidget, AutomationRule
from backend.api import devices, templates, automations, external, auth, mobile, platform_ops
from backend.websocket_hub import hub
from backend.hardware_gateway import hardware_gateway
import asyncio

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Axon IoT Core",
    description="High-performance, self-hosted IoT platform compatible with Blynk devices, widgets, and protocols",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("AXON_CORS_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000").split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProductionAuthMiddleware(BaseHTTPMiddleware):
    """Protect API routes when AXON_REQUIRE_AUTH=true.

    External device-token routes and the auth endpoints remain public because
    they are the protocol/API authentication boundaries themselves. The web
    UI can run in local development mode, while production deployments must
    explicitly enable this middleware and send bearer sessions.
    """

    async def dispatch(self, request: Request, call_next):
        if os.getenv("AXON_REQUIRE_AUTH", "false").lower() not in {"1", "true", "yes"}:
            return await call_next(request)
        path = request.url.path
        public = (
            path.startswith("/api/v1/auth/")
            or path.startswith("/external/api/")
            or path.startswith("/static/")
            or path in {"/", "/app", "/app.html", "/docs", "/openapi.json"}
        )
        if public or request.method == "OPTIONS":
            return await call_next(request)
        authorization = request.headers.get("authorization", "")
        if not authorization.startswith("Bearer "):
            return JSONResponse({"detail": "Authentication required"}, status_code=401)
        token = authorization.removeprefix("Bearer ").strip()
        if not token or token not in auth.SESSION_TOKENS:
            return JSONResponse({"detail": "Invalid or expired session"}, status_code=401)
        return await call_next(request)


app.add_middleware(ProductionAuthMiddleware)

# Include API routers
app.include_router(devices.router)
app.include_router(templates.router)
app.include_router(automations.router)
app.include_router(external.router)
app.include_router(auth.router)
app.include_router(auth.users_router)
app.include_router(mobile.router)
app.include_router(platform_ops.router)

@app.on_event("startup")
async def on_startup():
    hardware_gateway.hub = hub
    if hardware_gateway.server is None:
        asyncio.create_task(hardware_gateway.start())
    print("[Axon Core] Blynk Hardware Protocol Gateway started on TCP port 8080.")


# WebSocket endpoint matching ShellBridge specification
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await hub.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await hub.handle_message(websocket, data)
    except WebSocketDisconnect:
        hub.disconnect(websocket)
    except Exception as e:
        hub.disconnect(websocket)

# Seed initial database with full widget suite and datastreams
def seed_database():
    db = SessionLocal()
    try:
        if db.query(Organization).count() == 0:
            org = Organization(
                name="My organization - 2257TU",
                plan_tier="FREE",
                timezone="Africa/Lagos",
                server_region="ny3.blynk.cloud"
            )
            db.add(org)
            db.commit()
            db.refresh(org)

            user = User(
                org_id=org.id,
                email="samblynkk@gmail.com",
                password_hash=auth.hash_password(os.getenv("AXON_SEED_PASSWORD", "change-me")),
                name="Sam",
                role="Admin"
            )
            db.add(user)

            tmpl = DeviceTemplate(
                org_id=org.id,
                template_id="TMPL2yjltoB57",
                name="BLINKING LED",
                hardware_mcu="ESP32",
                connection_type="WI_FI",
                description="ESP32 Blinking LED Controller Template",
                firmware_config='#define BLYNK_TEMPLATE_ID "TMPL2yjltoB57"\n#define BLYNK_TEMPLATE_NAME "BLINKING LED"'
            )
            db.add(tmpl)
            db.commit()
            db.refresh(tmpl)

            dev = Device(
                org_id=org.id,
                template_id=tmpl.id,
                name="BLINKING LED",
                auth_token="yhdHK6Vuj2F6X7CUnX-QQIpuEl9Yy_dk",
                status="OFFLINE",
                firmware_version="1.0.0",
                blynk_library_version="1.3.5",
                heartbeat_interval=40
            )
            db.add(dev)

            # Datastreams V0 to V8
            ds_v0 = Datastream(
                template_id=tmpl.id, pin="V0", name="BLINKING LED",
                data_type="INTEGER", pin_type="VIRTUAL",
                min_value=0.0, max_value=1.0, step=1.0,
                default_value="0", current_value="0", units="", color_hex="#0375de"
            )
            db.add(ds_v0)

            ds_v1 = Datastream(
                template_id=tmpl.id, pin="V1", name="LED Brightness",
                data_type="INTEGER", pin_type="VIRTUAL",
                min_value=0.0, max_value=255.0, step=5.0,
                default_value="128", current_value="128", units="", color_hex="#10f17f"
            )
            db.add(ds_v1)

            ds_v2 = Datastream(
                template_id=tmpl.id, pin="V2", name="Temperature",
                data_type="DOUBLE", pin_type="VIRTUAL",
                min_value=-20.0, max_value=100.0, step=0.1,
                default_value="28.4", current_value="28.4", units="C", color_hex="#e0ff7b"
            )
            db.add(ds_v2)

            ds_v3 = Datastream(
                template_id=tmpl.id, pin="V3", name="Fan Relay",
                data_type="INTEGER", pin_type="VIRTUAL",
                min_value=0.0, max_value=1.0, step=1.0,
                default_value="1", current_value="1", units="", color_hex="#10f17f"
            )
            db.add(ds_v3)

            ds_v4 = Datastream(
                template_id=tmpl.id, pin="V4", name="Target Setpoint",
                data_type="DOUBLE", pin_type="VIRTUAL",
                min_value=16.0, max_value=32.0, step=0.5,
                default_value="24.0", current_value="24.0", units="C", color_hex="#0375de"
            )
            db.add(ds_v4)

            ds_v5 = Datastream(
                template_id=tmpl.id, pin="V5", name="Humidity",
                data_type="INTEGER", pin_type="VIRTUAL",
                min_value=0.0, max_value=100.0, step=1.0,
                default_value="62", current_value="62", units="%", color_hex="#38f394"
            )
            db.add(ds_v5)

            ds_v6 = Datastream(
                template_id=tmpl.id, pin="V6", name="Alarm State",
                data_type="INTEGER", pin_type="VIRTUAL",
                min_value=0.0, max_value=1.0, step=1.0,
                default_value="1", current_value="1", units="", color_hex="#fe0f00"
            )
            db.add(ds_v6)

            ds_v7 = Datastream(
                template_id=tmpl.id, pin="V7", name="CLI Terminal",
                data_type="STRING", pin_type="VIRTUAL",
                min_value=0.0, max_value=255.0, step=1.0,
                default_value="system ready", current_value="system ready", units="", color_hex="#8c8fa3"
            )
            db.add(ds_v7)

            # Widgets Setup
            w_btn = DashboardWidget(
                template_id=tmpl.id, widget_type="WEB_STYLED_BUTTON", label="LED Power", pin="V0",
                grid_x=0, grid_y=0, width=4, height=2,
                on_label="ON", off_label="OFF", on_color="#0375de", off_color="#fe0f00"
            )
            db.add(w_btn)

            w_slider = DashboardWidget(
                template_id=tmpl.id, widget_type="SLIDER", label="Brightness Level", pin="V1",
                grid_x=4, grid_y=0, width=4, height=2,
                settings={"min": 0, "max": 255, "step": 5}
            )
            db.add(w_slider)

            w_gauge = DashboardWidget(
                template_id=tmpl.id, widget_type="GAUGE", label="Ambient Temp", pin="V2",
                grid_x=8, grid_y=0, width=4, height=2,
                settings={"min": -20, "max": 100, "units": "C"}
            )
            db.add(w_gauge)

            w_switch = DashboardWidget(
                template_id=tmpl.id, widget_type="SWITCH", label="Fan Relay Switch", pin="V3",
                grid_x=0, grid_y=2, width=3, height=2
            )
            db.add(w_switch)

            w_stepper = DashboardWidget(
                template_id=tmpl.id, widget_type="NUMBER_INPUT", label="Temp Setpoint", pin="V4",
                grid_x=3, grid_y=2, width=3, height=2,
                settings={"min": 16.0, "max": 32.0, "step": 0.5, "units": "C"}
            )
            db.add(w_stepper)

            w_radial = DashboardWidget(
                template_id=tmpl.id, widget_type="RADIAL_GAUGE", label="Humidity Level", pin="V5",
                grid_x=6, grid_y=2, width=3, height=2,
                settings={"min": 0, "max": 100, "units": "%"}
            )
            db.add(w_radial)

            w_led = DashboardWidget(
                template_id=tmpl.id, widget_type="LED", label="System Alarm LED", pin="V6",
                grid_x=9, grid_y=2, width=3, height=2,
                settings={"color": "#fe0f00"}
            )
            db.add(w_led)

            w_chart = DashboardWidget(
                template_id=tmpl.id, widget_type="SUPERGRAPH", label="Telemetry Live SuperGraph", pin="V2",
                grid_x=0, grid_y=4, width=8, height=4,
                settings={"periods": ["1h", "6h", "1d", "1w"], "color": "#10f17f"}
            )
            db.add(w_chart)

            w_term = DashboardWidget(
                template_id=tmpl.id, widget_type="TERMINAL", label="Device Console Log", pin="V7",
                grid_x=8, grid_y=4, width=4, height=4
            )
            db.add(w_term)

            # Reverse-engineered mobile controls.  These are persisted fixture
            # definitions, not browser-created widgets, so the mobile canvas
            # remains a strict projection of SQLite.
            db.add(DashboardWidget(
                template_id=tmpl.id, widget_type="ICON_SEGMENTED", label="Operating Mode", pin="V3",
                grid_x=0, grid_y=8, width=6, height=2,
                settings={"options": ["AUTO", "ECO", "MANUAL", "BOOST"]}
            ))
            db.add(DashboardWidget(
                template_id=tmpl.id, widget_type="LEVEL_SLIDER_SWITCH", label="Level Control", pin="V1",
                grid_x=6, grid_y=8, width=6, height=2,
                settings={"min": 0, "max": 255, "step": 5}
            ))
            db.add(DashboardWidget(
                template_id=tmpl.id, widget_type="JOYSTICK", label="Directional Control", pin="V1",
                grid_x=0, grid_y=10, width=6, height=4
            ))
            db.add(DashboardWidget(
                template_id=tmpl.id, widget_type="ENHANCED_GAUGE", label="Enhanced Temperature", pin="V2",
                grid_x=6, grid_y=10, width=6, height=4,
                settings={"min": -20, "max": 100, "units": "C"}
            ))

            db.commit()
            print("Axon IoT database seeded with full Blynk widget suite.")

        # Seed Automation Rules if empty
        if db.query(AutomationRule).count() == 0:
            org_first = db.query(Organization).first()
            if org_first:
                r1 = AutomationRule(
                    org_id=org_first.id,
                    name="High Temp Cooling Trigger",
                    trigger_type="DATASTREAM_VALUE",
                    trigger_config={"condition": "When Temperature (V2) > 30 °C"},
                    action_type="WRITE_PIN",
                    action_config={"action": "Turn Fan Relay (V3) ON"},
                    is_active=True
                )
                r2 = AutomationRule(
                    org_id=org_first.id,
                    name="Daily System Diagnostic",
                    trigger_type="SCHEDULE",
                    trigger_config={"condition": "Schedule: Everyday at 08:00 AM"},
                    action_type="NOTIFICATION",
                    action_config={"action": "Log Status to Terminal (V7)"},
                    is_active=True
                )
                db.add(r1)
                db.add(r2)
                db.commit()
                print("Seeded automation rules.")
    finally:
        db.close()

# Re-seed if needed
seed_database()

# Serve static frontend files from the repository by default.  A deployment may
# override this with AXON_FRONTEND_DIR, but the checkout must work on Linux,
# macOS, and Windows without a machine-specific absolute path.
frontend_dir = Path(os.getenv("AXON_FRONTEND_DIR", Path(__file__).resolve().parent.parent / "frontend")).resolve()
if frontend_dir.is_dir():
    app.mount("/static", StaticFiles(directory=str(frontend_dir), html=False), name="static")

@app.get("/")
def serve_index():
    index_file = frontend_dir / "index.html"
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Axon IoT Core API is running."}

@app.get("/app")
@app.get("/app.html")
def serve_mobile_app():
    app_file = frontend_dir / "app.html"
    if os.path.exists(app_file):
        return FileResponse(app_file)
    return {"message": "Mobile App UI is running."}
