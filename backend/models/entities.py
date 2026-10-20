from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database import Base

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    plan_tier = Column(String(50), default="FREE")  # FREE, PRO, BUSINESS, ENTERPRISE
    timezone = Column(String(100), default="Africa/Lagos")
    server_region = Column(String(50), default="ny3.blynk.cloud")
    theme_config = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    users = relationship("User", back_populates="organization")
    templates = relationship("DeviceTemplate", back_populates="organization")
    devices = relationship("Device", back_populates="organization")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), default="")
    role = Column(String(50), default="Admin")  # Admin, Staff, User
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="users")

class DeviceTemplate(Base):
    __tablename__ = "device_templates"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    template_id = Column(String(50), unique=True, index=True, nullable=False)  # e.g. TMPL2yjltoB57
    name = Column(String(255), nullable=False)  # e.g. BLINKING LED
    hardware_mcu = Column(String(100), default="ESP32")  # ESP32, ESP8266, Arduino, Raspberry Pi
    connection_type = Column(String(50), default="WI_FI")  # WI_FI, BLE, ETHERNET, CELLULAR
    icon_name = Column(String(50), default="device-default")
    description = Column(Text, default="")
    firmware_config = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="templates")
    devices = relationship("Device", back_populates="template")
    datastreams = relationship("Datastream", back_populates="template")
    widgets = relationship("DashboardWidget", back_populates="template")

class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    template_id = Column(Integer, ForeignKey("device_templates.id"), nullable=False)
    name = Column(String(255), nullable=False)
    auth_token = Column(String(64), unique=True, index=True, nullable=False)
    status = Column(String(50), default="OFFLINE")  # ONLINE, OFFLINE, INACTIVE
    last_reported_at = Column(DateTime, nullable=True)
    last_connected_at = Column(DateTime, nullable=True)
    disconnected_at = Column(DateTime, nullable=True)
    firmware_version = Column(String(50), default="1.0.0")
    blynk_library_version = Column(String(50), default="1.3.5")
    heartbeat_interval = Column(Integer, default=40)
    ip_address = Column(String(45), nullable=True)
    metadata_fields = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="devices")
    template = relationship("DeviceTemplate", back_populates="devices")
    telemetry = relationship("TelemetryTimeSeries", back_populates="device")

class Datastream(Base):
    __tablename__ = "datastreams"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("device_templates.id"), nullable=False)
    pin = Column(String(10), nullable=False)  # V0, V1, D0, A0
    name = Column(String(255), nullable=False)
    data_type = Column(String(50), default="INTEGER")  # INTEGER, DOUBLE, STRING, ENUM, LOCATION
    pin_type = Column(String(50), default="VIRTUAL")  # VIRTUAL, DIGITAL, ANALOG
    min_value = Column(Float, default=0.0)
    max_value = Column(Float, default=1.0)
    step = Column(Float, default=1.0)
    default_value = Column(String(255), default="0")
    current_value = Column(String(255), default="0")
    units = Column(String(50), default="")
    color_hex = Column(String(20), default="#0375de")
    aggregation = Column(String(20), default="AVG")  # AVG, MIN, MAX, SUM, LIVE
    created_at = Column(DateTime, default=datetime.utcnow)

    template = relationship("DeviceTemplate", back_populates="datastreams")

class DashboardWidget(Base):
    __tablename__ = "dashboard_widgets"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("device_templates.id"), nullable=False)
    widget_type = Column(String(100), nullable=False)  # WEB_STYLED_BUTTON, GAUGE, SLIDER, SUPERGRAPH, LCD, TERMINAL
    label = Column(String(255), default="")
    pin = Column(String(10), nullable=False)  # Bound Virtual Pin
    grid_x = Column(Integer, default=0)
    grid_y = Column(Integer, default=0)
    width = Column(Integer, default=4)
    height = Column(Integer, default=2)
    on_label = Column(String(100), default="ON")
    off_label = Column(String(100), default="OFF")
    on_color = Column(String(20), default="#0375de")
    off_color = Column(String(20), default="#fe0f00")
    on_back_color = Column(String(20), default="#0375de1a")
    off_back_color = Column(String(20), default="#fe0f001a")
    settings = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    template = relationship("DeviceTemplate", back_populates="widgets")

class TelemetryTimeSeries(Base):
    __tablename__ = "telemetry_time_series"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    pin = Column(String(10), nullable=False)
    value = Column(String(255), nullable=False)
    numeric_value = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    device = relationship("Device", back_populates="telemetry")

class AutomationRule(Base):
    __tablename__ = "automation_rules"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    name = Column(String(255), nullable=False)
    trigger_type = Column(String(50), nullable=False)  # DEVICE_STATE, DATASTREAM_VALUE, SCHEDULE, GEOFENCE
    trigger_config = Column(JSON, default=dict)
    action_type = Column(String(50), nullable=False)   # WRITE_PIN, NOTIFICATION, EMAIL, WEBHOOK
    action_config = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
