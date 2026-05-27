"""
ALAS Context Engine.

Injects environmental and temporal context into the LLM prompt.
Allows ALAS to be aware of the time of day, system uptime, and context.
"""

from datetime import datetime
import psutil
import platform
import logging

logger = logging.getLogger("alas.proactive.context")

class ContextEngine:
    """Manages environmental context for ALAS."""
    
    def get_time_context(self) -> str:
        """Get a natural language string representing the current time/day."""
        now = datetime.now()
        hour = now.hour
        
        time_of_day = "night"
        if 5 <= hour < 12:
            time_of_day = "morning"
        elif 12 <= hour < 17:
            time_of_day = "afternoon"
        elif 17 <= hour < 22:
            time_of_day = "evening"
            
        return f"It is currently {time_of_day} ({now.strftime('%I:%M %p')}) on {now.strftime('%A, %B %d, %Y')}."
        
    def get_system_context(self) -> str:
        """Get brief system stats to inject into prompt if highly proactive."""
        try:
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time
            hours, remainder = divmod(int(uptime.total_seconds()), 3600)
            minutes, _ = divmod(remainder, 60)
            
            uptime_str = f"{hours}h {minutes}m"
            battery = psutil.sensors_battery()
            battery_str = f", Battery: {battery.percent}%" if battery else ""
            
            return f"System Uptime: {uptime_str}{battery_str}."
        except Exception as e:
            logger.debug(f"Failed to get system context: {e}")
            return ""

    def build_context_prompt(self, proactivity_threshold: float) -> str:
        """
        Builds the context string to be appended to the system prompt.
        Highly proactive ALAS gets more system context.
        """
        context = [self.get_time_context()]
        
        if proactivity_threshold > 0.6:
            sys_ctx = self.get_system_context()
            if sys_ctx:
                context.append(sys_ctx)
                
        if context:
            return "\n[ENVIRONMENTAL CONTEXT]:\n" + "\n".join(context)
        return ""

# Singleton
_context_engine = None

def get_context_engine() -> ContextEngine:
    global _context_engine
    if _context_engine is None:
        _context_engine = ContextEngine()
    return _context_engine
