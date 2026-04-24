"""
Tesla automation package.

Provides:
  - TeslaState: dataclass representing the full vehicle state
  - TeslaEvent: dataclass representing a single MQTT-driven state-change event
  - EventType: enum of every known MQTT topic / event kind
  - TeslaMQTTClient: MQTT listener that keeps TeslaState up-to-date and fires event callbacks
  - TeslaController: sends commands to the vehicle via Tesla Fleet API (teslapy)
"""

from tesla.models.state import TeslaState
from tesla.models.event import TeslaEvent, EventType
from tesla.mqtt_client import TeslaMQTTClient
from tesla.controller import TeslaController

__all__ = ["TeslaState", "TeslaEvent", "EventType", "TeslaMQTTClient", "TeslaController"]
