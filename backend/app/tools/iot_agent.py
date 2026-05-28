"""
ALAS IoT & Smart Home Agent — Phase 4

Provides tools to interface with Home Assistant (REST API) and MQTT.
"""
import os
import logging
import requests
from typing import Optional, Dict, Any

logger = logging.getLogger("alas.tools.iot")

# HASS Configurations (read from env or fallback to local mock/defaults)
HASS_URL = os.getenv("HASS_URL", "http://localhost:8123")
HASS_TOKEN = os.getenv("HASS_TOKEN", "")

# MQTT Configurations
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_USER", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")


def get_home_status(entity_id: str = "") -> str:
    """
    Get the state of smart home devices or sensors from Home Assistant.
    If entity_id is empty, returns a list of all active states.
    """
    if not HASS_TOKEN:
        return "Error: HASS_TOKEN environment variable is not set. Cannot connect to Home Assistant."

    headers = {
        "Authorization": f"Bearer {HASS_TOKEN}",
        "Content-Type": "application/json",
    }
    
    url = f"{HASS_URL}/api/states/{entity_id}" if entity_id else f"{HASS_URL}/api/states"
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if entity_id:
                state = data.get("state", "unknown")
                friendly_name = data.get("attributes", {}).get("friendly_name", entity_id)
                return f"Device '{friendly_name}' status: {state}"
            else:
                # Summarize active devices
                summary = []
                for entity in data[:30]:  # limit to 30 to avoid overwhelming LLM
                    ent_id = entity.get("entity_id")
                    state = entity.get("state")
                    friendly_name = entity.get("attributes", {}).get("friendly_name", ent_id)
                    summary.append(f"- {friendly_name} ({ent_id}): {state}")
                return "Home Assistant Active Devices:\n" + "\n".join(summary)
        else:
            return f"Failed to fetch Home Assistant state: HTTP {response.status_code}"
    except Exception as e:
        return f"Error connecting to Home Assistant: {e}"


def control_home_device(entity_id: str, action: str, parameters: Optional[Dict[str, Any]] = None) -> str:
    """
    Control a smart home device via Home Assistant (e.g. turn on, turn off, set brightness).
    
    Args:
        entity_id: The Home Assistant entity ID (e.g. 'light.living_room').
        action: The service action (e.g. 'turn_on', 'turn_off', 'toggle').
        parameters: Optional dictionary of attributes (e.g. {"brightness": 120}).
    """
    if not HASS_TOKEN:
        return "Error: HASS_TOKEN environment variable is not set. Cannot control Home Assistant."

    headers = {
        "Authorization": f"Bearer {HASS_TOKEN}",
        "Content-Type": "application/json",
    }
    
    # Derive domain (e.g. light, switch, climate)
    domain = entity_id.split('.')[0] if '.' in entity_id else 'homeassistant'
    
    url = f"{HASS_URL}/api/services/{domain}/{action}"
    payload = {"entity_id": entity_id}
    if parameters:
        payload.update(parameters)
        
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=5)
        if response.status_code == 200:
            return f"🟢 Successfully executed service '{action}' on device '{entity_id}'."
        else:
            return f"Failed to execute service: HTTP {response.status_code} - {response.text}"
    except Exception as e:
        return f"Error executing service on Home Assistant: {e}"


def publish_mqtt_message(topic: str, message: str) -> str:
    """
    Publish a message to an MQTT broker.
    Used for custom DIY automation and sensor triggers.
    """
    try:
        import paho.mqtt.publish as publish
    except ImportError:
        return "Error: paho-mqtt package is not installed. Run: pip install paho-mqtt"
        
    try:
        auth = None
        if MQTT_USER and MQTT_PASSWORD:
            auth = {'username': MQTT_USER, 'password': MQTT_PASSWORD}
            
        publish.single(
            topic=topic,
            payload=message,
            hostname=MQTT_BROKER,
            port=MQTT_PORT,
            auth=auth,
            timeout=5
        )
        return f"🟢 Published message to topic '{topic}' successfully."
    except Exception as e:
        return f"Failed to publish MQTT message to '{topic}': {e}"
