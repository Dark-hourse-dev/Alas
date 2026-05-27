"""
ALAS Desktop Notifier.

Sends proactive system notifications to the user using the native desktop environment.
"""

import subprocess
import logging
from typing import Optional

logger = logging.getLogger("alas.proactive.notifier")

class Notifier:
    """Sends desktop notifications."""

    def __init__(self):
        # We assume notify-send is available on Linux
        self._command = "notify-send"

    def send(self, title: str, message: str, urgency: str = "normal", icon: Optional[str] = "dialog-information"):
        """
        Send a desktop notification.
        
        Args:
            title: The title of the notification.
            message: The body text.
            urgency: 'low', 'normal', or 'critical'.
            icon: Icon name or path to image file.
        """
        try:
            cmd = [self._command, "-u", urgency]
            if icon:
                cmd.extend(["-i", icon])
            cmd.extend([title, message])
            
            subprocess.run(cmd, check=True, capture_output=True)
            logger.debug(f"Notification sent: {title}")
        except FileNotFoundError:
            logger.warning("notify-send not found. Desktop notifications disabled.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to send notification: {e.stderr.decode()}")
        except Exception as e:
            logger.error(f"Error sending notification: {e}")

# Singleton
_notifier: Optional[Notifier] = None

def get_notifier() -> Notifier:
    global _notifier
    if _notifier is None:
        _notifier = Notifier()
    return _notifier
