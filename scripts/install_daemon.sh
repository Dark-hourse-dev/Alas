#!/bin/bash
# ========================================================
# ALAS System Daemon Installer — Phase 3.5
# Sets up ALAS to start automatically when you log into Linux
#
# Features:
#   • systemd user service for the FastAPI backend
#   • systemd user service for the system tray icon
#   • .env environment injection
#   • Health-check wait after startup
#   • Uninstall option
# ========================================================

set -e

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "  ╔══════════════════════════════════════╗"
echo "  ║  🧬 ALAS System Daemon Installer     ║"
echo "  ║  Phase 3.5 — Always-On Integration   ║"
echo "  ╚══════════════════════════════════════╝"
echo -e "${NC}"

# --- Uninstall mode ---
if [[ "$1" == "--uninstall" ]]; then
    echo -e "${YELLOW}Uninstalling ALAS services...${NC}"
    systemctl --user stop alas.service 2>/dev/null || true
    systemctl --user stop alas-tray.service 2>/dev/null || true
    systemctl --user stop alas-wake.service 2>/dev/null || true
    systemctl --user disable alas.service 2>/dev/null || true
    systemctl --user disable alas-tray.service 2>/dev/null || true
    systemctl --user disable alas-wake.service 2>/dev/null || true
    rm -f "$HOME/.config/systemd/user/alas.service"
    rm -f "$HOME/.config/systemd/user/alas-tray.service"
    rm -f "$HOME/.config/systemd/user/alas-wake.service"
    systemctl --user daemon-reload
    echo -e "${GREEN}✅ ALAS services uninstalled.${NC}"
    exit 0
fi

# --- Setup paths ---
PROJECT_DIR=$(cd "$(dirname "$0")" && pwd)
VENV_PYTHON="$PROJECT_DIR/venv/bin/python"
ENV_FILE="$PROJECT_DIR/.env"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$SERVICE_DIR/alas.service"
TRAY_SERVICE_FILE="$SERVICE_DIR/alas-tray.service"
WAKE_SERVICE_FILE="$SERVICE_DIR/alas-wake.service"

# --- Verify virtual environment ---
if [ ! -f "$VENV_PYTHON" ]; then
    echo -e "${RED}❌ Virtual environment not found at $VENV_PYTHON${NC}"
    echo "Please create it first:"
    echo "  cd $PROJECT_DIR && python3 -m venv venv && source venv/bin/activate && pip install -r backend/requirements.txt"
    exit 1
fi

# --- Load .env variables for the service ---
ENV_LINES=""
if [ -f "$ENV_FILE" ]; then
    echo -e "${GREEN}📦 Loading environment from .env${NC}"
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        [[ "$key" =~ ^#.*$ ]] && continue
        [[ -z "$key" ]] && continue
        # Remove surrounding quotes from value
        value=$(echo "$value" | sed 's/^["'"'"']//;s/["'"'"']$//')
        ENV_LINES+="Environment=\"$key=$value\"\n"
    done < "$ENV_FILE"
else
    echo -e "${YELLOW}⚠️  No .env file found. Using defaults.${NC}"
fi

# --- Create systemd user directory ---
mkdir -p "$SERVICE_DIR"

# ========================================================
# Service 1: ALAS Backend (FastAPI + Uvicorn)
# ========================================================
echo -e "${CYAN}📝 Creating ALAS backend service...${NC}"

cat <<EOF > "$SERVICE_FILE"
[Unit]
Description=ALAS — Adaptive Living AI System (Backend)
After=network.target ollama.service
Wants=ollama.service

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR
ExecStart=$VENV_PYTHON -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

# Environment
Environment="PATH=$PROJECT_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"
$(echo -e "$ENV_LINES")

# Resource limits (prevent runaway usage)
MemoryMax=2G
CPUQuota=80%

[Install]
WantedBy=default.target
EOF

# ========================================================
# Service 2: ALAS System Tray Icon
# ========================================================
echo -e "${CYAN}📝 Creating ALAS tray service...${NC}"

cat <<EOF > "$TRAY_SERVICE_FILE"
[Unit]
Description=ALAS — System Tray Icon
After=alas.service graphical-session.target
Requires=alas.service
PartOf=graphical-session.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR
ExecStartPre=/bin/sleep 3
ExecStart=$VENV_PYTHON -m backend.app.tray
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

Environment="PATH=$PROJECT_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="DISPLAY=:0"
$(echo -e "$ENV_LINES")

[Install]
WantedBy=default.target
EOF

# ========================================================
# Service 3: ALAS Wake Word Engine ("Hey ALAS")
# ========================================================
echo -e "${CYAN}📝 Creating ALAS wake word service...${NC}"

cat <<EOF > "$WAKE_SERVICE_FILE"
[Unit]
Description=ALAS — Wake Word Engine
After=alas.service
Requires=alas.service

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR
ExecStartPre=/bin/sleep 5
ExecStart=$VENV_PYTHON wake_daemon.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

Environment="PATH=$PROJECT_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"
$(echo -e "$ENV_LINES")

[Install]
WantedBy=default.target
EOF

# ========================================================
# Reload, Enable, Start
# ========================================================
echo -e "${CYAN}⚙️  Reloading systemd...${NC}"
systemctl --user daemon-reload

echo -e "${CYAN}⚙️  Enabling services for auto-start on login...${NC}"
systemctl --user enable alas.service
systemctl --user enable alas-tray.service
systemctl --user enable alas-wake.service

# Enable lingering so services start even before the user logs into a desktop
loginctl enable-linger "$USER" 2>/dev/null || true

echo -e "${CYAN}🚀 Starting ALAS backend...${NC}"
systemctl --user restart alas.service

# --- Health check wait ---
echo -e "${YELLOW}⏳ Waiting for ALAS to become healthy...${NC}"
MAX_WAIT=30
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if curl -sf http://localhost:8000/api/status > /dev/null 2>&1; then
        echo -e "${GREEN}✅ ALAS backend is online!${NC}"
        break
    fi
    sleep 1
    WAITED=$((WAITED + 1))
    echo -n "."
done
echo ""

if [ $WAITED -ge $MAX_WAIT ]; then
    echo -e "${RED}⚠️  ALAS backend didn't respond within ${MAX_WAIT}s.${NC}"
    echo "Check logs: journalctl --user -u alas -f"
else
    # Start the tray and wake word only after backend is healthy
    echo -e "${CYAN}🖥️  Starting system tray and wake word engine...${NC}"
    systemctl --user restart alas-tray.service 2>/dev/null || true
    systemctl --user restart alas-wake.service 2>/dev/null || true
fi

# ========================================================
# Done!
# ========================================================
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅ ALAS System Daemon installed successfully!           ║${NC}"
echo -e "${GREEN}║                                                          ║${NC}"
echo -e "${GREEN}║  ALAS will now auto-start silently when you log in.      ║${NC}"
echo -e "${GREEN}║  The system tray icon shows live status.                 ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}⚙️  Useful Commands:${NC}"
echo "  • Backend status:    systemctl --user status alas"
echo "  • Tray status:       systemctl --user status alas-tray"
echo "  • Wake engine status:systemctl --user status alas-wake"
echo "  • Live logs:         journalctl --user -f -u alas -u alas-wake"
echo "  • Stop ALAS:         systemctl --user stop alas"
echo "  • Restart ALAS:      systemctl --user restart alas"
echo "  • Uninstall:         bash install_daemon.sh --uninstall"
echo ""
echo -e "${CYAN}🌐 Open ALAS:${NC}  http://localhost:8000"
echo ""
