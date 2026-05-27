"""
ALAS System Tray Application — Phase 3.5

A lightweight system tray icon that:
  • Shows live server status (🟢 Online / 🔴 Offline)
  • Displays recent action count from the Permission Tier system
  • Provides quick-access menu: Open UI, System Info, Logs, Restart, Quit
  • Sends desktop notifications for important events
"""

import threading
import time
import webbrowser
import subprocess
import sys
import json
import logging
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
    import pystray
    from pystray import MenuItem as item
except ImportError:
    print("Please install pystray and Pillow: pip install pystray Pillow")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("Please install requests: pip install requests")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | ALAS-Tray | %(message)s")
logger = logging.getLogger("alas.tray")

# Local ALAS server
ALAS_URL = "http://localhost:8000"

# State
_status_data = {
    "status": "starting",
    "version": "?",
    "phase": "?",
    "actions_logged": 0,
}


def get_status():
    """Ping the ALAS server and return rich status data."""
    global _status_data
    try:
        response = requests.get(f"{ALAS_URL}/api/status", timeout=3)
        if response.status_code == 200:
            data = response.json()
            _status_data = {
                "status": data.get("status", "online"),
                "version": data.get("version", "?"),
                "phase": data.get("phase", "?"),
                "actions_logged": data.get("actions_logged", 0),
            }
            return "🟢 Online"
    except Exception:
        _status_data["status"] = "offline"
    return "🔴 Offline"


def send_notification(title: str, message: str):
    """Send a desktop notification (Linux)."""
    try:
        subprocess.run(
            ["notify-send", "--app-name=ALAS", "--icon=dialog-information", title, message],
            timeout=5,
            capture_output=True,
        )
    except Exception as e:
        logger.warning(f"Notification failed: {e}")


def open_ui(icon, item):
    """Open the ALAS frontend in the default browser."""
    webbrowser.open(ALAS_URL)


def open_permissions(icon, item):
    """Open the permissions dashboard."""
    webbrowser.open(f"{ALAS_URL}/#permissions")


def show_system_info(icon, item):
    """Show a notification with system info from ALAS."""
    try:
        # Try to get system info via the ALAS API
        response = requests.get(f"{ALAS_URL}/api/status", timeout=3)
        if response.status_code == 200:
            data = response.json()
            msg = (
                f"Version: {data.get('version', '?')}\n"
                f"Phase: {data.get('phase', '?')}\n"
                f"Actions logged: {data.get('actions_logged', 0)}"
            )
            send_notification("ALAS System Info", msg)
    except Exception as e:
        send_notification("ALAS Error", f"Could not fetch status: {e}")


def view_logs(icon, item):
    """Open a terminal showing ALAS logs."""
    try:
        subprocess.Popen(
            ["x-terminal-emulator", "-e", "journalctl --user -u alas -f"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        try:
            subprocess.Popen(
                ["gnome-terminal", "--", "journalctl", "--user", "-u", "alas", "-f"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            logger.error(f"Failed to open terminal: {e}")


def restart_alas(icon, item):
    """Restart the ALAS backend service."""
    try:
        result = subprocess.run(
            ["systemctl", "--user", "restart", "alas"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            send_notification("ALAS", "🔄 Backend restarting...")
        else:
            send_notification("ALAS Error", f"Restart failed: {result.stderr}")
    except Exception as e:
        logger.error(f"Restart failed: {e}")


def exit_app(icon, item):
    """Exit the system tray application."""
    icon.stop()


def create_status_icon(online: bool) -> Image.Image:
    """Create a dynamic tray icon with status indicator."""
    icon_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "assets" / "icon-512.png"

    if icon_path.exists():
        try:
            image = Image.open(icon_path).convert("RGBA")
            image.thumbnail((64, 64))
        except Exception:
            image = Image.new("RGBA", (64, 64), color=(99, 102, 241, 255))
    else:
        # Fallback: create a simple icon
        image = Image.new("RGBA", (64, 64), color=(99, 102, 241, 255))

    # Draw a status dot in the bottom-right corner
    draw = ImageDraw.Draw(image)
    dot_color = (34, 197, 94, 255) if online else (239, 68, 68, 255)  # green / red
    dot_radius = 10
    x, y = 50, 50
    draw.ellipse(
        [x - dot_radius, y - dot_radius, x + dot_radius, y + dot_radius],
        fill=dot_color,
        outline=(0, 0, 0, 128),
        width=1,
    )

    return image


def setup(icon):
    """Background thread to update the icon and tooltip with server status."""
    icon.visible = True
    was_offline = True  # Track transitions for notifications

    while icon.visible:
        status_text = get_status()
        is_online = "Online" in status_text

        # Update tooltip with rich info
        tooltip = f"ALAS — {status_text}"
        if is_online:
            tooltip += f" | v{_status_data['version']}"
            tooltip += f" | {_status_data['actions_logged']} actions"

        icon.title = tooltip

        # Update icon with status dot
        try:
            icon.icon = create_status_icon(is_online)
        except Exception:
            pass

        # Notify on status transitions
        if is_online and was_offline:
            send_notification("ALAS", "🟢 ALAS is now online and ready!")
        elif not is_online and not was_offline:
            send_notification("ALAS", "🔴 ALAS backend went offline.")

        was_offline = not is_online
        time.sleep(5)


def main():
    # Initial icon
    image = create_status_icon(False)

    # Create tray menu
    menu = pystray.Menu(
        item("Open ALAS UI", open_ui, default=True),
        item("Permissions Dashboard", open_permissions),
        pystray.Menu.SEPARATOR,
        item("System Info", show_system_info),
        item("View Logs", view_logs),
        item("Restart Backend", restart_alas),
        pystray.Menu.SEPARATOR,
        item("Exit Tray", exit_app),
    )

    # Initialize tray icon
    icon = pystray.Icon("ALAS", image, "ALAS — Starting...", menu)

    logger.info("🧬 ALAS System Tray starting...")

    # Run the icon with the background status updater
    icon.run(setup)


if __name__ == "__main__":
    main()
