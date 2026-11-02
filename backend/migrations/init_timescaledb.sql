-- ==============================================================================
-- Axon IoT Enterprise TimescaleDB Hypertable Setup
-- Designed for hosting millions of IoT devices and billions of time-series rows
-- ==============================================================================

-- 1. Enable TimescaleDB Extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- 2. Ensure composite indexes for high-speed device-pin lookups
CREATE INDEX IF NOT EXISTS idx_telemetry_device_pin_time 
ON telemetry_time_series (device_id, pin, timestamp DESC);

-- 3. Convert telemetry_time_series into a Hypertable partitioned by time (7-day intervals)
SELECT create_hypertable(
    'telemetry_time_series',
    'timestamp',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE,
    migrate_data => TRUE
);

-- 4. Enable Native TimescaleDB Columnar Compression (Yields 90-95% disk savings)
ALTER TABLE telemetry_time_series SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'device_id, pin',
    timescaledb.compress_orderby = 'timestamp DESC'
);

-- 5. Automatically compress chunks older than 14 days
SELECT add_compression_policy('telemetry_time_series', INTERVAL '14 days', if_not_exists => TRUE);

-- 6. Add Automated Retention Policy (Auto-drop chunks older than 2 years / 730 days)
SELECT add_retention_policy('telemetry_time_series', INTERVAL '730 days', if_not_exists => TRUE);

-- 7. Continuous Aggregate for SuperChart Performance (1-hour downsampled averages)
CREATE MATERIALIZED VIEW IF NOT EXISTS telemetry_hourly_agg
WITH (timescaledb.continuous) AS
SELECT 
    device_id,
    pin,
    time_bucket('1 hour', timestamp) AS bucket,
    AVG(numeric_value) AS avg_value,
    MIN(numeric_value) AS min_value,
    MAX(numeric_value) AS max_value,
    COUNT(*) AS sample_count
FROM telemetry_time_series
WHERE numeric_value IS NOT NULL
GROUP BY device_id, pin, bucket
WITH NO DATA;

-- Refresh policy for continuous aggregate
SELECT add_continuous_aggregate_policy('telemetry_hourly_agg',
    start_offset => INTERVAL '30 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);
