import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from backend.database import engine, Base, SessionLocal
from backend.models.entities import Organization, User, DeviceTemplate, Device, Datastream, DashboardWidget
from backend.api import devices, templates
from backend.websocket_hub import hub

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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(devices.router)
app.include_router(templates.router)

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

# Seed initial database from captured Blynk payloads if empty
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
                password_hash="argon2_hash_placeholder",
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
                status="ONLINE",
                firmware_version="1.0.0",
                blynk_library_version="1.3.5",
                heartbeat_interval=40
            )
            db.add(dev)

            ds_v0 = Datastream(
                template_id=tmpl.id,
                pin="V0",
                name="BLINKING LED",
                data_type="INTEGER",
                pin_type="VIRTUAL",
                min_value=0.0,
                max_value=1.0,
                step=1.0,
                default_value="0",
                current_value="0",
                units="",
                color_hex="#0375de",
                aggregation="AVG"
            )
            db.add(ds_v0)

            # Add extra standard datastreams for demonstration
            ds_v1 = Datastream(
                template_id=tmpl.id,
                pin="V1",
                name="LED Brightness",
                data_type="INTEGER",
                pin_type="VIRTUAL",
                min_value=0.0,
                max_value=255.0,
                step=5.0,
                default_value="128",
                current_value="128",
                units="",
                color_hex="#10f17f"
            )
            db.add(ds_v1)

            ds_v2 = Datastream(
                template_id=tmpl.id,
                pin="V2",
                name="Temperature",
                data_type="DOUBLE",
                pin_type="VIRTUAL",
                min_value=-20.0,
                max_value=100.0,
                step=0.1,
                default_value="28.4",
                current_value="28.4",
                units="°C",
                color_hex="#e0ff7b"
            )
            db.add(ds_v2)

            # Web Widgets: Button, Slider, Gauge, SuperGraph
            w_btn = DashboardWidget(
                template_id=tmpl.id,
                widget_type="WEB_STYLED_BUTTON",
                label="LED Power",
                pin="V0",
                grid_x=0,
                grid_y=0,
                width=4,
                height=2,
                on_label="ON",
                off_label="OFF",
                on_color="#0375de",
                off_color="#fe0f00",
                on_back_color="#0375de1a",
                off_back_color="#fe0f001a"
            )
            db.add(w_btn)

            w_slider = DashboardWidget(
                template_id=tmpl.id,
                widget_type="SLIDER",
                label="Brightness Level",
                pin="V1",
                grid_x=4,
                grid_y=0,
                width=4,
                height=2,
                settings={"min": 0, "max": 255, "step": 5}
            )
            db.add(w_slider)

            w_gauge = DashboardWidget(
                template_id=tmpl.id,
                widget_type="GAUGE",
                label="Ambient Temp",
                pin="V2",
                grid_x=8,
                grid_y=0,
                width=4,
                height=2,
                settings={"min": -20, "max": 100, "units": "°C"}
            )
            db.add(w_gauge)

            w_chart = DashboardWidget(
                template_id=tmpl.id,
                widget_type="SUPERGRAPH",
                label="Telemetry History (V2)",
                pin="V2",
                grid_x=0,
                grid_y=2,
                width=12,
                height=4,
                settings={"periods": ["1h", "6h", "1d", "1w"], "color": "#10f17f"}
            )
            db.add(w_chart)

            db.commit()
            print("Axon IoT database seeded with Blynk core template and device specifications.")
    finally:
        db.close()

seed_database()

# Serve static frontend files
frontend_dir = r"C:\RE\axon_iot\frontend"
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/")
def serve_index():
    index_file = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Axon IoT Core API is running. Build frontend/index.html to view dashboard."}
