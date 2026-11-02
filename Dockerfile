# ==============================================================================
# Axon IoT (Blynk Compatibility Clone) - Production Multi-Transport Dockerfile
# Exposes Port 8000 (HTTP/REST/WebSocket/Static) and Port 8080 (Blynk TCP Wire)
# ==============================================================================
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    AXON_HARDWARE_PORT=8080 \
    DATABASE_URL="sqlite:////data/axon_iot.db" \
    AXON_REQUIRE_AUTH=false \
    AXON_CORS_ORIGINS="*"

# Install system dependencies (curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY backend ./backend
COPY frontend ./frontend
COPY firmware ./firmware
COPY run_server.py .
COPY README.md .

# Create volume directory for persistent SQLite database
RUN mkdir -p /data

# Expose web console / REST port (8000) and Blynk hardware TCP protocol port (8080)
EXPOSE 8000 8080

# Health check verifies web API & database connectivity
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/api/v1/health || exit 1

# Launch Axon IoT Dual-Gateway Server
CMD ["python", "run_server.py"]
