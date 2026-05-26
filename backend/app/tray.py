import threading
import time
import webbrowser
import requests
import sys
from pathlib import Path

try:
    from PIL import Image
    import pystray
    from pystray import MenuItem as item
except ImportError:
    print("Please install pystray and Pillow: pip install pystray Pillow")
    sys.exit(1)

# Local ALAS server
ALAS_URL = "http://localhost:8000"

def get_status():
    """Ping the ALAS server to check if it's online."""
    try:
        response = requests.get(f"{ALAS_URL}/api/status", timeout=2)
        if response.status_code == 200:
            return "🟢 Online"
    except Exception:
        pass
    return "🔴 Offline"

def open_ui(icon, item):
    """Open the ALAS frontend in the default browser."""
    webbrowser.open(ALAS_URL)

def exit_app(icon, item):
    """Exit the system tray application."""
    icon.stop()

def setup(icon):
    """Background thread to update the icon tooltip with the server status."""
    icon.visible = True
    while icon.visible:
        status = get_status()
        icon.title = f"ALAS — {status}"
        time.sleep(5)

def main():
    # Load the ALAS icon, or fallback to a solid color if missing
    icon_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "assets" / "icon-512.png"
    if icon_path.exists():
        image = Image.open(icon_path)
        # Resize for tray to save memory
        image.thumbnail((64, 64))
    else:
        image = Image.new('RGB', (64, 64), color=(99, 102, 241)) # Indigo

    # Create tray menu
    menu = pystray.Menu(
        item('Open ALAS UI', open_ui, default=True),
        pystray.Menu.SEPARATOR,
        item('Exit Tray', exit_app)
    )

    # Initialize tray icon
    icon = pystray.Icon("ALAS", image, "ALAS — Starting...", menu)
    
    # Run the icon with the background status updater
    icon.run(setup)

if __name__ == "__main__":
    main()
