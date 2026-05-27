"""
ALAS System Monitors.

Background jobs that check system health and user activity,
and trigger proactive behaviors via the Notifier or ALAS LLM.
"""

import psutil
import logging
from datetime import datetime

from backend.app.proactive.notifier import get_notifier
from backend.app.learning.evolution import get_evolution_system

logger = logging.getLogger("alas.proactive.monitors")

class SystemMonitor:
    def __init__(self):
        self.notifier = get_notifier()
        self.evolution = get_evolution_system()
        
    def check_disk_space(self):
        """Check disk usage and notify if it's getting full."""
        # Only act proactively if proactivity_threshold is met
        genome = self.evolution.current_genome
        if genome.get("proactivity_threshold", 0.5) < 0.3:
            return # Too reactive to care
            
        try:
            usage = psutil.disk_usage('/')
            percent = usage.percent
            
            if percent > 90:
                self.notifier.send(
                    title="ALAS Alert: Disk Space Critical",
                    message=f"Root partition is {percent}% full. Consider freeing up some space.",
                    urgency="critical",
                    icon="drive-harddisk"
                )
                logger.warning(f"Disk space critical: {percent}%")
            elif percent > 80 and genome.get("proactivity_threshold", 0.5) > 0.6:
                # If highly proactive, warn earlier
                self.notifier.send(
                    title="ALAS Notice: Disk Space",
                    message=f"Root partition is {percent}% full.",
                    urgency="normal",
                    icon="drive-harddisk"
                )
        except Exception as e:
            logger.error(f"Failed to check disk space: {e}")

    def check_memory_usage(self):
        """Check RAM usage."""
        genome = self.evolution.current_genome
        if genome.get("proactivity_threshold", 0.5) < 0.4:
            return
            
        try:
            mem = psutil.virtual_memory()
            percent = mem.percent
            
            if percent > 90:
                self.notifier.send(
                    title="ALAS Alert: High Memory Usage",
                    message=f"System RAM is at {percent}%. Performance may degrade.",
                    urgency="critical",
                    icon="cpu"
                )
        except Exception as e:
            logger.error(f"Failed to check memory: {e}")

# Singleton
_monitor = None

def get_monitor() -> SystemMonitor:
    global _monitor
    if _monitor is None:
        _monitor = SystemMonitor()
    return _monitor

def register_monitors(scheduler):
    """Register all monitor jobs with the scheduler."""
    monitor = get_monitor()
    
    # Register callbacks
    scheduler.register_callback("sysmon_disk", monitor.check_disk_space)
    scheduler.register_callback("sysmon_ram", monitor.check_memory_usage)
    
    # Check if they exist, if not, create them
    existing_callbacks = [t.get("callback") for t in scheduler.get_tasks()]
    
    if "sysmon_disk" not in existing_callbacks:
        # Check every 12 hours
        scheduler.add_recurring("Disk Space Monitor", "sysmon_disk", interval_minutes=720)
        
    if "sysmon_ram" not in existing_callbacks:
        # Check every hour
        scheduler.add_recurring("RAM Usage Monitor", "sysmon_ram", interval_minutes=60)
        
    logger.info("System monitors registered.")
