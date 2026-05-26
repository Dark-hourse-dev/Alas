#!/bin/bash
# ========================================================
# ALAS System Daemon Installer
# Sets up ALAS to start automatically when you log into Linux
# ========================================================

echo "🧬 Installing ALAS System Daemon..."

# Setup paths
PROJECT_DIR=$(pwd)
VENV_PYTHON="$PROJECT_DIR/venv/bin/python"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$SERVICE_DIR/alas.service"

# Verify virtual environment
if [ ! -f "$VENV_PYTHON" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run this script from the project root where the venv/ folder is located."
    exit 1
fi

# Create systemd user directory if it doesn't exist
mkdir -p "$SERVICE_DIR"

# Generate the systemd service file
cat <<EOF > "$SERVICE_FILE"
[Unit]
Description=ALAS — Adaptive Living AI System
After=network.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR
ExecStart=$VENV_PYTHON -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

# Set environment variables for the service
Environment="PATH=$PROJECT_DIR/venv/bin:/usr/bin:/bin"

[Install]
WantedBy=default.target
EOF

# Reload systemd, enable the service, and start it
systemctl --user daemon-reload
systemctl --user enable alas.service
systemctl --user start alas.service

echo ""
echo "✅ ALAS System Daemon installed and started successfully!"
echo "ALAS will now automatically boot silently in the background whenever you log into your PC."
echo ""
echo "⚙️  Useful Commands:"
echo "  • Check status:  systemctl --user status alas"
echo "  • View logs:     journalctl --user -u alas -f"
echo "  • Stop ALAS:     systemctl --user stop alas"
echo "  • Restart ALAS:  systemctl --user restart alas"
echo ""

# Optional: Prompt to start the system tray icon
echo "Would you like to start the System Tray Icon now? (y/n)"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])+$ ]]; then
    echo "Starting tray icon..."
    nohup $VENV_PYTHON backend/app/tray.py > /dev/null 2>&1 &
    echo "✅ Tray icon started! Check your system tray."
fi
