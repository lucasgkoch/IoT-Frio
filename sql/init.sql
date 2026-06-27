CREATE TABLE IF NOT EXISTS sensor_readings (
    id BIGSERIAL PRIMARY KEY,
    topic TEXT NOT NULL,
    device_id TEXT NOT NULL,
    device_type TEXT,
    timestamp_sensor TIMESTAMPTZ,
    timestamp_received TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    temperature_c NUMERIC(6,2),
    temperature_min_c NUMERIC(6,2),
    temperature_max_c NUMERIC(6,2),
    power_kw NUMERIC(10,3),
    door_open BOOLEAN,
    compressor_on BOOLEAN,
    battery_pct INTEGER,
    rssi INTEGER,
    raw_payload JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS sensor_alerts (
    id BIGSERIAL PRIMARY KEY,
    reading_id BIGINT REFERENCES sensor_readings(id),
    device_id TEXT NOT NULL,
    timestamp_alert TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    alert_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sensor_readings_device_timestamp
ON sensor_readings (device_id, timestamp_sensor DESC);

CREATE INDEX IF NOT EXISTS idx_sensor_alerts_device_timestamp
ON sensor_alerts (device_id, timestamp_alert DESC);

CREATE INDEX IF NOT EXISTS idx_sensor_alerts_type
ON sensor_alerts (alert_type);