"""
ALAS Embodied Intelligence — Drone Agent (Phase 7.1)

Provides tools to connect to and command aerial drones using the MAVLink protocol.
"""
import time
import logging
from typing import Dict, Any

logger = logging.getLogger("alas.embodied.drone")


class DroneAgent:
    """Agent for controlling MAVLink compatible drones."""
    
    def __init__(self):
        self.master = None
        self.connected = False

    def connect(self, connection_string: str = 'tcp:127.0.0.1:5760') -> str:
        """Connect to a MAVLink drone (e.g., SITL simulator or real drone via telemetry)."""
        try:
            from pymavlink import mavutil
        except ImportError:
            return "Error: pymavlink is not installed. Run 'pip install pymavlink'."

        try:
            logger.info(f"🚁 Connecting to drone at {connection_string}...")
            # For phase 7 mock, we might not have a real SITL running, so we catch timeouts
            self.master = mavutil.mavlink_connection(connection_string, autoreconnect=True)
            self.master.wait_heartbeat(timeout=3.0)
            
            if self.master.target_system == 0:
                return "Failed to receive drone heartbeat within 3 seconds. Is the drone/simulator running?"
                
            self.connected = True
            logger.info(f"🚁 Connected to Drone System {self.master.target_system}")
            return f"✅ Successfully connected to MAVLink drone at {connection_string}."
        except Exception as e:
            logger.error(f"Failed to connect to drone: {e}")
            return f"Error connecting to drone: {e}"

    def command_takeoff(self, altitude: float = 10.0) -> str:
        """Command the drone to take off to a specific altitude."""
        if not self.connected:
            return "Error: Drone is not connected."
        if altitude <= 0 or altitude > 500:
            return f"Error: Altitude must be between 0 and 500 meters. Got: {altitude}"
            
        try:
            from pymavlink import mavutil
            
            # Arm the drone
            self.master.mav.command_long_send(
                self.master.target_system,
                self.master.target_component,
                mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                0,
                1, 0, 0, 0, 0, 0, 0)
                
            # Send takeoff command
            self.master.mav.command_long_send(
                self.master.target_system,
                self.master.target_component,
                mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
                0,
                0, 0, 0, 0, 0, 0, altitude)
                
            return f"🚁 Command Sent: ARM and TAKEOFF to {altitude} meters."
        except Exception as e:
            return f"Error sending takeoff command: {e}"

    def command_land(self) -> str:
        """Command the drone to land at its current position."""
        if not self.connected:
            return "Error: Drone is not connected."
            
        try:
            from pymavlink import mavutil
            self.master.mav.command_long_send(
                self.master.target_system,
                self.master.target_component,
                mavutil.mavlink.MAV_CMD_NAV_LAND,
                0,
                0, 0, 0, 0, 0, 0, 0)
                
            return "🚁 Command Sent: LAND at current position."
        except Exception as e:
            return f"Error sending land command: {e}"


# Global instance
_drone_agent = DroneAgent()

def execute_drone_command(action: str, **kwargs) -> str:
    """Tool wrapper for LLM to execute drone commands."""
    if action == "connect":
        conn_str = kwargs.get("connection_string", "tcp:127.0.0.1:5760")
        return _drone_agent.connect(conn_str)
    elif action == "takeoff":
        alt = kwargs.get("altitude", 10.0)
        return _drone_agent.command_takeoff(alt)
    elif action == "land":
        return _drone_agent.command_land()
    else:
        return f"Unknown drone action: {action}. Available: connect, takeoff, land."
