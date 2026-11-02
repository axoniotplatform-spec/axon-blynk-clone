"""
database.py — High-Concurrency Multi-Engine Database Layer for Axon IoT
Supports:
1. Enterprise PostgreSQL + TimescaleDB (for production hosting of millions of devices and billions of telemetry rows)
2. SQLite (for local embedded development and lightweight single-file testing)

Features:
- Automated URI normalization (postgres:// -> postgresql://)
- Connection Pool Tuning (QueuePool with pre-ping, auto-recycle, and scalable overflow)
- TimescaleDB Hypertable auto-detection and hypertable initialization for telemetry_time_series
"""

import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool, NullPool, StaticPool

logger = logging.getLogger("axon.database")

raw_db_url = os.getenv("DATABASE_URL", "sqlite:///C:/RE/axon_iot/axon_iot.db")

# Normalize cloud PostgreSQL URLs (e.g. Render, Heroku, Supabase use postgres://)
if raw_db_url.startswith("postgres://"):
    DATABASE_URL = raw_db_url.replace("postgres://", "postgresql://", 1)
else:
    DATABASE_URL = raw_db_url

is_postgres = "postgresql" in DATABASE_URL or "postgres" in DATABASE_URL

if is_postgres:
    # High-concurrency connection pool for PostgreSQL / TimescaleDB
    pool_size = int(os.getenv("AXON_DB_POOL_SIZE", "30"))
    max_overflow = int(os.getenv("AXON_DB_MAX_OVERFLOW", "50"))
    pool_timeout = int(os.getenv("AXON_DB_POOL_TIMEOUT", "30"))
    
    engine = create_engine(
        DATABASE_URL,
        poolclass=QueuePool,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_recycle=1800,
        pool_pre_ping=True
    )
    logger.info(f"[Database] Initialized PostgreSQL connection pool (size={pool_size}, max_overflow={max_overflow})")
else:
    # Embedded SQLite for local dev / tests
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    logger.info("[Database] Initialized SQLite embedded engine")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_timescaledb_if_available():
    """
    If connected to PostgreSQL, checks for TimescaleDB extension and partitions
    the telemetry_time_series table into a high-performance hypertable capable of
    hosting hundreds of millions of data points with native 90% compression.
    """
    if not is_postgres:
        return {"status": "sqlite_mode", "hypertable": False}

    with engine.connect() as conn:
        try:
            # Check if timescaledb extension is available
            ext_check = conn.execute(text("SELECT extname FROM pg_extension WHERE extname = 'timescaledb'")).fetchone()
            if not ext_check:
                try:
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"))
                    conn.commit()
                    ext_check = True
                except Exception as e:
                    logger.info(f"[TimescaleDB] Extension not installed on PostgreSQL host: {e}")
                    return {"status": "standard_postgres", "hypertable": False}

            # Convert telemetry_time_series into hypertable partitioned by timestamp (7-day intervals)
            conn.execute(text("""
                SELECT create_hypertable(
                    'telemetry_time_series',
                    'timestamp',
                    chunk_time_interval => INTERVAL '7 days',
                    if_not_exists => TRUE
                );
            """))
            conn.commit()

            # Enable compression policy (compress chunks older than 14 days)
            try:
                conn.execute(text("""
                    ALTER TABLE telemetry_time_series SET (
                        timescaledb.compress,
                        timescaledb.compress_segmentby = 'device_id, pin'
                    );
                    SELECT add_compression_policy('telemetry_time_series', INTERVAL '14 days', if_not_exists => TRUE);
                """))
                conn.commit()
                logger.info("[TimescaleDB] Successfully enabled hypertable compression policy on telemetry_time_series")
            except Exception as comp_err:
                logger.debug(f"[TimescaleDB] Compression policy skipped or already enabled: {comp_err}")

            return {"status": "timescaledb_active", "hypertable": True}
        except Exception as e:
            logger.warning(f"[TimescaleDB] Hypertable setup encountered notice: {e}")
            return {"status": "standard_postgres", "hypertable": False, "notice": str(e)}
