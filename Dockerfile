# ============================================
# ALAS — Adaptive Living AI System
# Docker container for cloud deployment
# ============================================

FROM python:3.12-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set workdir
WORKDIR /app

# Copy requirements first (for caching)
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy project
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY .env.example ./.env

# Create data dirs
RUN mkdir -p backend/data

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/status || exit 1

# Run ALAS
CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
