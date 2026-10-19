-- ==============================================================================
-- Axon IoT Platform - Production Relational Schema
-- Architecture: Exact 1:1 Mirror of Blynk Cloud IoT Entity Model
-- Generated on: 2026-10-19T22:39:02.336589
-- Dialect: PostgreSQL / CockroachDB / Standard SQL
-- ==============================================================================

-- 1. Organizations Table
CREATE TABLE IF NOT EXISTS organizations (
    id BIGINT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    parent_id BIGINT DEFAULT NULL,
    timezone VARCHAR(100) DEFAULT 'UTC',
    plan_tier VARCHAR(50) DEFAULT 'FREE',
    primary_color VARCHAR(20) DEFAULT '#0375de',
    secondary_color VARCHAR(20) DEFAULT '#979282',
    logo_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Users Table
CREATE TABLE IF NOT EXISTS users (
    id BIGINT PRIMARY KEY,
    organization_id BIGINT REFERENCES organizations(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'Admin',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Device Templates Table
CREATE TABLE IF NOT EXISTS device_templates (
    id VARCHAR(100) PRIMARY KEY,
    organization_id BIGINT REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    hardware_type VARCHAR(50) DEFAULT 'MCU',
    connection_type VARCHAR(50) DEFAULT 'WI_FI',
    icon_name VARCHAR(50) DEFAULT 'e874',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Devices Table
CREATE TABLE IF NOT EXISTS devices (
    id BIGINT PRIMARY KEY,
    organization_id BIGINT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    owner_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    template_id VARCHAR(100) REFERENCES device_templates(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    auth_token VARCHAR(64) UNIQUE NOT NULL,
    status VARCHAR(50) DEFAULT 'OFFLINE',
    connection_type VARCHAR(50) DEFAULT 'WI_FI',
    ip_address INET,
    country VARCHAR(100),
    latitude NUMERIC(9, 6),
    longitude NUMERIC(9, 6),
    firmware_version VARCHAR(50) DEFAULT '0.0.0',
    library_version VARCHAR(50) DEFAULT '1.3.5',
    heartbeat_interval INT DEFAULT 40,
    activated_at TIMESTAMP WITH TIME ZONE,
    last_reported_at TIMESTAMP WITH TIME ZONE,
    last_connected_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. Datastreams Table (Virtual & Physical Pins: V0, V1...)
CREATE TABLE IF NOT EXISTS datastreams (
    id BIGINT PRIMARY KEY,
    device_id BIGINT NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    pin INT NOT NULL,
    pin_type VARCHAR(50) DEFAULT 'VIRTUAL', -- VIRTUAL, DIGITAL, ANALOG
    name VARCHAR(255) NOT NULL,
    data_type VARCHAR(50) DEFAULT 'INT',   -- INT, DOUBLE, STRING, ENUM
    units VARCHAR(50) DEFAULT 'None',
    min_value NUMERIC(12, 4) DEFAULT 0,
    max_value NUMERIC(12, 4) DEFAULT 1,
    step_value NUMERIC(12, 4) DEFAULT 1,
    default_value TEXT DEFAULT '0',
    current_value TEXT DEFAULT '0',
    color VARCHAR(20) DEFAULT '#b2d9af',
    aggregation_type VARCHAR(20) DEFAULT 'AVG',
    value_updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_device_pin UNIQUE (device_id, pin, pin_type)
);

-- 6. Widgets Table (Dashboard UI Layout, Button States, Dials)
CREATE TABLE IF NOT EXISTS widgets (
    id BIGINT PRIMARY KEY,
    device_id BIGINT NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    datastream_id BIGINT REFERENCES datastreams(id) ON DELETE SET NULL,
    type VARCHAR(100) NOT NULL,             -- WEB_STYLED_BUTTON, GAUGE, CHART
    label VARCHAR(255),
    pos_x INT NOT NULL DEFAULT 0,
    pos_y INT NOT NULL DEFAULT 0,
    width INT NOT NULL DEFAULT 4,
    height INT NOT NULL DEFAULT 1,
    style VARCHAR(50) DEFAULT 'SOLID',
    edge VARCHAR(50) DEFAULT 'ROUNDED',
    font_size VARCHAR(50) DEFAULT 'MEDIUM',
    on_button_state JSONB,                  -- text, textColor, backgroundColor, icon
    off_button_state JSONB,                 -- text, textColor, backgroundColor, icon
    config_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. Telemetry Time Series Table (High-Frequency Influx / Sensor Log)
CREATE TABLE IF NOT EXISTS telemetry_time_series (
    id BIGSERIAL PRIMARY KEY,
    device_id BIGINT NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    datastream_id BIGINT NOT NULL REFERENCES datastreams(id) ON DELETE CASCADE,
    pin INT NOT NULL,
    value_numeric NUMERIC(16, 6),
    value_string TEXT,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Performance & Query Optimization Indexes
CREATE INDEX IF NOT EXISTS idx_devices_org ON devices(organization_id);
CREATE INDEX IF NOT EXISTS idx_devices_token ON devices(auth_token);
CREATE INDEX IF NOT EXISTS idx_datastreams_device ON datastreams(device_id);
CREATE INDEX IF NOT EXISTS idx_widgets_device ON widgets(device_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_device_time ON telemetry_time_series(device_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_pin_time ON telemetry_time_series(device_id, pin, recorded_at DESC);
