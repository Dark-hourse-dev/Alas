"""
ALAS Permission Tier System — Phase 3.5

Three-tier autonomy control for all agentic actions:
  🟢 AUTO   — Safe, read-only operations. Execute without asking.
  🟡 NOTIFY — Moderate-risk actions. Execute and notify the user.
  🔴 ASK    — Destructive / high-risk. Block until user confirms.

The system starts with sensible defaults and learns user preferences
over time via the `permission_memory` store.
"""

import json
import logging
import re
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, Tuple

from backend.app.config import get_settings

logger = logging.getLogger("alas.safety.permissions")


# ---------------------------------------------------------------------------
# Permission tiers
# ---------------------------------------------------------------------------

class PermissionTier(str, Enum):
    AUTO = "auto"       # 🟢 No approval needed
    NOTIFY = "notify"   # 🟡 Execute, then notify
    ASK = "ask"         # 🔴 Must ask first


# ---------------------------------------------------------------------------
# Pattern-based classification for shell commands
# ---------------------------------------------------------------------------

# 🟢 AUTO — harmless, read-only commands
AUTO_PATTERNS = [
    r"^ls\b",
    r"^cat\b",
    r"^head\b",
    r"^tail\b",
    r"^echo\b",
    r"^pwd$",
    r"^whoami$",
    r"^date$",
    r"^uptime$",
    r"^uname\b",
    r"^which\b",
    r"^whereis\b",
    r"^file\b",
    r"^wc\b",
    r"^du\b",
    r"^df\b",
    r"^free\b",
    r"^top\s+-bn1",
    r"^htop\b",
    r"^ps\b",
    r"^hostname$",
    r"^git\s+status",
    r"^git\s+log",
    r"^git\s+diff",
    r"^git\s+branch",
    r"^git\s+remote\b",
    r"^python3?\s+--version",
    r"^node\s+--version",
    r"^npm\s+--version",
    r"^pip\s+list",
    r"^pip\s+show",
    r"^pip\s+--version",
    r"^env$",
    r"^printenv\b",
    r"^lsblk\b",
    r"^ip\s+a",
    r"^ifconfig\b",
    r"^ping\s+-c\s+\d",
    r"^curl\s+-s",
    r"^find\b.*-name\b",
    r"^grep\b",
    r"^rg\b",
    r"^bat\b",
]

# 🟡 NOTIFY — moderate risk, side-effects but recoverable
NOTIFY_PATTERNS = [
    r"^mkdir\b",
    r"^touch\b",
    r"^cp\b",
    r"^mv\b",
    r"^git\s+add\b",
    r"^git\s+commit\b",
    r"^git\s+push\b",
    r"^git\s+pull\b",
    r"^git\s+checkout\b",
    r"^git\s+merge\b",
    r"^git\s+stash\b",
    r"^pip\s+install\b",
    r"^npm\s+install\b",
    r"^yarn\s+add\b",
    r"^cargo\s+add\b",
    r"^apt\s+list\b",
    r"^brew\s+install\b",
    r"^chmod\b",
    r"^chown\b",
    r"^tar\b",
    r"^zip\b",
    r"^unzip\b",
    r"^wget\b",
    r"^curl\b(?!.*-s)",  # curl without -s might download
    r"^docker\s+ps\b",
    r"^docker\s+images\b",
    r"^systemctl\s+status\b",
    r"^journalctl\b",
]

# 🔴 ASK — dangerous, destructive, or escalated
ASK_PATTERNS = [
    r"^rm\b",
    r"^rmdir\b",
    r"^sudo\b",
    r"^su\b",
    r"\brm\s+-rf\b",
    r"^dd\b",
    r"^mkfs\b",
    r"^fdisk\b",
    r"^parted\b",
    r"^shutdown\b",
    r"^reboot\b",
    r"^poweroff\b",
    r"^systemctl\s+(start|stop|restart|enable|disable)\b",
    r"^kill\b",
    r"^killall\b",
    r"^pkill\b",
    r"^apt\s+(install|remove|purge|upgrade)\b",
    r"^apt-get\b",
    r"^dpkg\b",
    r"^snap\s+install\b",
    r"^docker\s+(run|rm|stop|kill|exec)\b",
    r"^iptables\b",
    r"^ufw\b",
    r"^crontab\b",
    r"\|.*rm\b",            # piped into rm
    r">\s*/dev/",           # writing to devices
    r">\s*/etc/",           # writing to system config
    r">\s*/usr/",           # writing to system dirs
    r";\s*rm\b",            # chained rm
    r"&&\s*rm\b",           # chained rm
    r"\beval\b",
    r"\bexec\b",
    r"^python.*-c\b",       # arbitrary python execution
    r"^node.*-e\b",         # arbitrary node execution
    r"\bcurl\b.*\|\s*(ba)?sh",  # curl pipe to shell
]


# ---------------------------------------------------------------------------
# Permission Manager
# ---------------------------------------------------------------------------

class PermissionManager:
    """
    Classifies commands into permission tiers based on pattern matching
    and user-defined overrides. Persists learned preferences to disk.
    """

    def __init__(self):
        settings = get_settings()
        self.data_dir = Path(settings.chroma_persist_dir).parent / "permissions"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.overrides_file = self.data_dir / "user_overrides.json"
        self.action_log_file = self.data_dir / "action_log.jsonl"

        # User-defined permanent overrides  {"command_pattern": "auto|notify|ask"}
        self.user_overrides: Dict[str, str] = self._load_overrides()

        # Pending approvals  {request_id: {command, tier, status}}
        self.pending: Dict[str, dict] = {}

    # ----- Classification -----

    def classify_command(self, command: str) -> Tuple[PermissionTier, str]:
        """
        Classify a shell command and return (tier, reason).
        Checks user overrides first, then pattern lists, defaulting to ASK.
        """
        cmd_stripped = command.strip()

        # 1. Check user overrides
        for pattern, tier_str in self.user_overrides.items():
            if re.search(pattern, cmd_stripped, re.IGNORECASE):
                tier = PermissionTier(tier_str)
                return tier, f"User override matched: {pattern}"

        # 2. Check ASK patterns first (highest priority for safety)
        for pattern in ASK_PATTERNS:
            if re.search(pattern, cmd_stripped, re.IGNORECASE):
                return PermissionTier.ASK, f"Matches dangerous pattern: {pattern}"

        # 3. Check AUTO patterns
        for pattern in AUTO_PATTERNS:
            if re.search(pattern, cmd_stripped, re.IGNORECASE):
                return PermissionTier.AUTO, f"Matches safe pattern: {pattern}"

        # 4. Check NOTIFY patterns
        for pattern in NOTIFY_PATTERNS:
            if re.search(pattern, cmd_stripped, re.IGNORECASE):
                return PermissionTier.NOTIFY, f"Matches moderate pattern: {pattern}"

        # 5. Default: ASK for anything unrecognized
        return PermissionTier.ASK, "Unknown command — defaulting to ASK tier for safety."

    def is_allowed(self, command: str) -> Tuple[bool, PermissionTier, str]:
        """
        Determine if a command can execute immediately.
        Returns (allowed, tier, reason).
        - AUTO → (True, ...)
        - NOTIFY → (True, ...)
        - ASK → (False, ...) — must wait for user approval
        """
        tier, reason = self.classify_command(command)

        if tier == PermissionTier.ASK:
            return False, tier, reason

        return True, tier, reason

    # ----- Action log -----

    def log_action(self, command: str, tier: str, result: str, approved_by: str = "auto"):
        """Append an entry to the action audit log."""
        import datetime
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "command": command,
            "tier": tier,
            "result": result[:500],  # truncate
            "approved_by": approved_by,
        }
        try:
            with open(self.action_log_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to write action log: {e}")

    # ----- User overrides -----

    def add_override(self, pattern: str, tier: str):
        """Let the user permanently override a command pattern's tier."""
        if tier not in [t.value for t in PermissionTier]:
            raise ValueError(f"Invalid tier: {tier}. Must be auto/notify/ask.")
        self.user_overrides[pattern] = tier
        self._save_overrides()
        logger.info(f"Permission override added: '{pattern}' → {tier}")

    def remove_override(self, pattern: str):
        """Remove a user override."""
        if pattern in self.user_overrides:
            del self.user_overrides[pattern]
            self._save_overrides()

    def get_overrides(self) -> Dict[str, str]:
        return dict(self.user_overrides)

    def get_recent_actions(self, limit: int = 20) -> list:
        """Read the last N entries from the action log."""
        if not self.action_log_file.exists():
            return []
        try:
            with open(self.action_log_file, "r") as f:
                lines = f.readlines()
            entries = []
            for line in lines[-limit:]:
                try:
                    entries.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    pass
            return entries
        except Exception:
            return []

    # ----- Persistence helpers -----

    def _load_overrides(self) -> Dict[str, str]:
        if self.overrides_file.exists():
            try:
                with open(self.overrides_file, "r") as f:
                    return json.loads(f.read())
            except Exception as e:
                logger.error(f"Failed to load permission overrides: {e}")
        return {}

    def _save_overrides(self):
        try:
            with open(self.overrides_file, "w") as f:
                f.write(json.dumps(self.user_overrides, indent=2))
        except Exception as e:
            logger.error(f"Failed to save permission overrides: {e}")


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_permission_manager: Optional[PermissionManager] = None


def get_permission_manager() -> PermissionManager:
    global _permission_manager
    if _permission_manager is None:
        _permission_manager = PermissionManager()
    return _permission_manager
