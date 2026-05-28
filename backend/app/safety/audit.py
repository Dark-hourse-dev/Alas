import os
import json
import logging
from typing import Dict, Any
import datetime

logger = logging.getLogger("alas.safety.audit")

class AuditTrail:
    """
    ALAS Audit Trail System (Phase 9 Security).
    Ensures every significant action taken by the AI is logged immutably,
    providing transparency and reversibility where possible.
    """
    
    def __init__(self, log_dir: str = "~/.alas/audit"):
        self.log_dir = os.path.expanduser(log_dir)
        os.makedirs(self.log_dir, exist_ok=True)
        self.current_log = os.path.join(self.log_dir, f"audit_{datetime.date.today().isoformat()}.jsonl")
        logger.info(f"🔒 Audit Trail initialized. Logging to: {self.current_log}")
        
    def log_action(self, actor: str, action_type: str, details: Dict[str, Any], risk_level: str = "low"):
        """
        Log an action to the audit trail.
        risk_level: 'low', 'medium', 'high', 'critical'
        """
        entry = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "actor": actor,
            "action": action_type,
            "risk_level": risk_level,
            "details": details
        }
        
        try:
            with open(self.current_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
                
            if risk_level in ["high", "critical"]:
                logger.warning(f"⚠️ HIGH RISK ACTION LOGGED: {action_type} by {actor}")
        except Exception as e:
            logger.error(f"Failed to write to audit trail: {e}")
            
    def export_trail(self) -> str:
        """Return the path to the current audit trail for user export."""
        return self.current_log
