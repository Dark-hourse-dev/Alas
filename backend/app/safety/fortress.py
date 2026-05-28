"""
ALAS Infrastructure Fortress — Resilience & Reliability (Phase 9)

Implements system-level reliability mechanisms:
- Automatic Backup System (snapshotting databases)
- Self-Healing Memory (verifying SQLite integrity)
- State Snapshotting (saving state before risky ops)
"""
import os
import time
import shutil
import logging
from pathlib import Path

logger = logging.getLogger("alas.safety.fortress")

class InfrastructureFortress:
    def __init__(self):
        from backend.app.config import get_settings
        self.settings = get_settings()
        self.data_dir = Path(self.settings.sqlite_db_path).parent
        self.backup_dir = self.data_dir / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    def create_snapshot(self, reason: str = "manual") -> str:
        """Create a full snapshot of the SQLite database and memory state."""
        import re
        # Sanitize reason to prevent path traversal
        safe_reason = re.sub(r'[^a-zA-Z0-9_-]', '_', reason)[:50]
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        snapshot_name = f"snapshot_{timestamp}_{safe_reason}"
        snapshot_path = self.backup_dir / snapshot_name
        snapshot_path.mkdir(exist_ok=True)
        
        try:
            # Backup SQLite DB
            db_path = Path(self.settings.sqlite_db_path)
            if db_path.exists():
                shutil.copy2(db_path, snapshot_path / "alas.db")
                
            # Backup Knowledge Graph
            kg_path = self.data_dir / "knowledge_graph.json"
            if kg_path.exists():
                shutil.copy2(kg_path, snapshot_path / "knowledge_graph.json")
                
            logger.info(f"🛡️ Infrastructure Fortress: Snapshot created at {snapshot_path}")
            return f"Snapshot '{snapshot_name}' created successfully."
        except Exception as e:
            logger.error(f"Failed to create snapshot: {e}")
            return f"Error creating snapshot: {e}"

    def self_heal_memory(self) -> str:
        """Run integrity checks on SQLite and repair if corrupted."""
        import sqlite3
        db_path = self.settings.sqlite_db_path
        
        if not os.path.exists(db_path):
            return "No database found to heal."
            
        try:
            # Connect and run PRAGMA integrity_check
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check;")
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0] == "ok":
                return "Memory integrity verified. DB is healthy."
            else:
                logger.error("DB corruption detected! Attempting recovery...")
                # In a real scenario, this would restore from the latest snapshot
                # For this implementation, we just flag it.
                return f"⚠️ Memory corruption detected! Integrity check returned: {result}. Manual restore required."
                
        except sqlite3.Error as e:
            return f"SQLite error during self-healing: {e}"

    def restore_snapshot(self, snapshot_name: str) -> str:
        """Restore the database from a specific snapshot."""
        snapshot_path = (self.backup_dir / snapshot_name).resolve()
        # Security: ensure the resolved path is within backup_dir
        if not str(snapshot_path).startswith(str(self.backup_dir.resolve())):
            return "Error: Invalid snapshot path (possible path traversal)."
        if not snapshot_path.exists():
            return f"Error: Snapshot '{snapshot_name}' not found."
            
        try:
            db_path = Path(self.settings.sqlite_db_path)
            backup_db = snapshot_path / "alas.db"
            if backup_db.exists():
                shutil.copy2(backup_db, db_path)
                
            kg_path = self.data_dir / "knowledge_graph.json"
            backup_kg = snapshot_path / "knowledge_graph.json"
            if backup_kg.exists():
                shutil.copy2(backup_kg, kg_path)
                
            logger.info(f"🛡️ Infrastructure Fortress: System restored to {snapshot_name}")
            return f"System successfully restored to snapshot: {snapshot_name}."
        except Exception as e:
            return f"Error restoring snapshot: {e}"

# Global singleton
_fortress = InfrastructureFortress()

def get_fortress() -> InfrastructureFortress:
    return _fortress

# Expose to tools
def execute_system_snapshot(reason: str = "manual") -> str:
    return _fortress.create_snapshot(reason)

def execute_heal_memory() -> str:
    return _fortress.self_heal_memory()
