"""
TeslaEvent – a single state-change event emitted by TeslaMQTTClient.

Every time TeslaMate publishes a new value on an MQTT topic, the client
creates a TeslaEvent and passes it to all registered callbacks.  The event
carries:

  - ``event_type``  – which aspect of the vehicle changed (EventType enum)
  - ``topic_key``   – the raw MQTT topic suffix (e.g. ``"battery_level"``)
  - ``old_value``   – the previous Python-typed value (None if first receipt)
  - ``new_value``   – the new Python-typed value
  - ``raw_payload`` – the original UTF-8 string from MQTT
  - ``timestamp``   – wall-clock time the message was received
  - ``state``       – a snapshot of the full TeslaState *after* this update
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from tesla.models.state import TeslaState


class EventType(str, Enum):
    """
    Categorises every MQTT topic that TeslaMate publishes.

    The enum value is the MQTT topic suffix (last path segment).  This makes
    it trivial to map a raw topic string to an EventType:

        event_type = EventType(topic_key)   # raises ValueError if unknown
        event_type = EventType.from_topic(topic_key)  # returns UNKNOWN safely
    """

    # ------------------------------------------------------------------ #
    # Identity / health
    # ------------------------------------------------------------------ #
    DISPLAY_NAME = "display_name"
    STATE = "state"
    HEALTHY = "healthy"

    # ------------------------------------------------------------------ #
    # Battery & charging
    # ------------------------------------------------------------------ #
    BATTERY_LEVEL = "battery_level"
    USABLE_BATTERY_LEVEL = "usable_battery_level"
    CHARGE_LIMIT_SOC = "charge_limit_soc"
    CHARGE_LIMIT_SOC_STD = "charge_limit_soc_std"
    CHARGE_LIMIT_SOC_MIN = "charge_limit_soc_min"
    CHARGE_LIMIT_SOC_MAX = "charge_limit_soc_max"
    EST_BATTERY_RANGE_KM = "est_battery_range_km"
    RATED_BATTERY_RANGE_KM = "rated_battery_range_km"
    IDEAL_BATTERY_RANGE_KM = "ideal_battery_range_km"
    PLUGGED_IN = "plugged_in"
    CHARGE_PORT_DOOR_OPEN = "charge_port_door_open"
    CHARGING_STATE = "charging_state"
    CHARGER_POWER = "charger_power"
    CHARGER_VOLTAGE = "charger_voltage"
    CHARGER_ACTUAL_CURRENT = "charger_actual_current"
    CHARGER_PHASES = "charger_phases"
    CHARGE_ENERGY_ADDED = "charge_energy_added"
    CHARGE_LIMIT_SOC_REACHED = "charge_limit_soc_reached"
    SCHEDULED_CHARGING_START_TIME = "scheduled_charging_start_time"
    TIME_TO_FULL_CHARGE = "time_to_full_charge"

    # ------------------------------------------------------------------ #
    # Climate / temperature
    # ------------------------------------------------------------------ #
    INSIDE_TEMP = "inside_temp"
    OUTSIDE_TEMP = "outside_temp"
    IS_CLIMATE_ON = "is_climate_on"
    IS_PRECONDITIONING = "is_preconditioning"
    CLIMATE_KEEPER_MODE = "climate_keeper_mode"
    DRIVER_TEMP_SETTING = "driver_temp_setting"
    PASSENGER_TEMP_SETTING = "passenger_temp_setting"
    FAN_STATUS = "fan_status"
    IS_REAR_DEFROSTER_ON = "is_rear_defroster_on"
    IS_FRONT_DEFROSTER_ON = "is_front_defroster_on"

    # ------------------------------------------------------------------ #
    # Ventilation / windows
    # ------------------------------------------------------------------ #
    WINDOWS_OPEN = "windows_open"
    DRIVER_FRONT_WINDOW_OPEN = "driver_front_window_open"
    PASSENGER_FRONT_WINDOW_OPEN = "passenger_front_window_open"
    DRIVER_REAR_WINDOW_OPEN = "driver_rear_window_open"
    PASSENGER_REAR_WINDOW_OPEN = "passenger_rear_window_open"

    # ------------------------------------------------------------------ #
    # Doors & trunk
    # ------------------------------------------------------------------ #
    DOORS_OPEN = "doors_open"
    DRIVER_FRONT_DOOR_OPEN = "driver_front_door_open"
    DRIVER_REAR_DOOR_OPEN = "driver_rear_door_open"
    PASSENGER_FRONT_DOOR_OPEN = "passenger_front_door_open"
    PASSENGER_REAR_DOOR_OPEN = "passenger_rear_door_open"
    TRUNK_OPEN = "trunk_open"
    FRUNK_OPEN = "frunk_open"

    # ------------------------------------------------------------------ #
    # Security
    # ------------------------------------------------------------------ #
    LOCKED = "locked"
    SENTRY_MODE = "sentry_mode"

    # ------------------------------------------------------------------ #
    # Location & motion
    # ------------------------------------------------------------------ #
    LATITUDE = "latitude"
    LONGITUDE = "longitude"
    HEADING = "heading"
    SPEED = "speed"
    ELEVATION = "elevation"
    ODOMETER = "odometer"
    SHIFT_STATE = "shift_state"

    # ------------------------------------------------------------------ #
    # Power & energy
    # ------------------------------------------------------------------ #
    POWER = "power"

    # ------------------------------------------------------------------ #
    # Accessories & misc
    # ------------------------------------------------------------------ #
    IS_USER_PRESENT = "is_user_present"
    KEEP_ACCESSORY_POWER_ON = "keep_accessory_power_on"
    CENTER_DISPLAY_STATE = "center_display_state"

    # ------------------------------------------------------------------ #
    # Tyre pressure monitoring (TPMS)
    # ------------------------------------------------------------------ #
    TPMS_PRESSURE_FL = "tpms_pressure_fl"
    TPMS_PRESSURE_FR = "tpms_pressure_fr"
    TPMS_PRESSURE_RL = "tpms_pressure_rl"
    TPMS_PRESSURE_RR = "tpms_pressure_rr"
    TPMS_SOFT_WARNING_FL = "tpms_soft_warning_fl"
    TPMS_SOFT_WARNING_FR = "tpms_soft_warning_fr"
    TPMS_SOFT_WARNING_RL = "tpms_soft_warning_rl"
    TPMS_SOFT_WARNING_RR = "tpms_soft_warning_rr"

    # ------------------------------------------------------------------ #
    # Active route / navigation
    # ------------------------------------------------------------------ #
    ACTIVE_ROUTE = "active_route"
    ACTIVE_ROUTE_DESTINATION = "active_route_destination"
    ACTIVE_ROUTE_LATITUDE = "active_route_latitude"
    ACTIVE_ROUTE_LONGITUDE = "active_route_longitude"
    LOCATION = "location"

    # ------------------------------------------------------------------ #
    # Charging current limits
    # ------------------------------------------------------------------ #
    CHARGE_CURRENT_REQUEST = "charge_current_request"
    CHARGE_CURRENT_REQUEST_MAX = "charge_current_request_max"

    # ------------------------------------------------------------------ #
    # Vehicle identity / trim
    # ------------------------------------------------------------------ #
    MODEL = "model"
    TRIM_BADGING = "trim_badging"
    EXTERIOR_COLOR = "exterior_color"
    SPOILER_TYPE = "spoiler_type"
    WHEEL_TYPE = "wheel_type"
    SINCE = "since"

    # ------------------------------------------------------------------ #
    # Software
    # ------------------------------------------------------------------ #
    VERSION = "version"
    UPDATE_AVAILABLE = "update_available"
    UPDATE_VERSION = "update_version"

    # ------------------------------------------------------------------ #
    # Catch-all for topics not yet mapped
    # ------------------------------------------------------------------ #
    UNKNOWN = "unknown"

    # ------------------------------------------------------------------ #
    # Class-level helpers
    # ------------------------------------------------------------------ #

    @classmethod
    def from_topic(cls, topic_key: str) -> "EventType":
        """
        Return the EventType matching *topic_key*, or ``EventType.UNKNOWN``
        if the topic is not recognised.

        Parameters
        ----------
        topic_key:
            The last segment of the MQTT topic path (e.g. ``"battery_level"``).
        """
        try:
            return cls(topic_key.lower())
        except ValueError:
            return cls.UNKNOWN

    # Convenience groupings ----------------------------------------------- #

    @classmethod
    def charging_events(cls) -> frozenset["EventType"]:
        """All event types related to charging."""
        return frozenset({
            cls.PLUGGED_IN,
            cls.CHARGE_PORT_DOOR_OPEN,
            cls.CHARGING_STATE,
            cls.CHARGER_POWER,
            cls.CHARGER_VOLTAGE,
            cls.CHARGER_ACTUAL_CURRENT,
            cls.CHARGER_PHASES,
            cls.CHARGE_ENERGY_ADDED,
            cls.CHARGE_LIMIT_SOC,
            cls.CHARGE_LIMIT_SOC_REACHED,
            cls.SCHEDULED_CHARGING_START_TIME,
            cls.TIME_TO_FULL_CHARGE,
        })

    @classmethod
    def battery_events(cls) -> frozenset["EventType"]:
        """All event types related to battery state."""
        return frozenset({
            cls.BATTERY_LEVEL,
            cls.USABLE_BATTERY_LEVEL,
            cls.CHARGE_LIMIT_SOC,
            cls.CHARGE_LIMIT_SOC_STD,
            cls.CHARGE_LIMIT_SOC_MIN,
            cls.CHARGE_LIMIT_SOC_MAX,
            cls.EST_BATTERY_RANGE_KM,
            cls.RATED_BATTERY_RANGE_KM,
            cls.IDEAL_BATTERY_RANGE_KM,
        })

    @classmethod
    def climate_events(cls) -> frozenset["EventType"]:
        """All event types related to climate / temperature."""
        return frozenset({
            cls.INSIDE_TEMP,
            cls.OUTSIDE_TEMP,
            cls.IS_CLIMATE_ON,
            cls.IS_PRECONDITIONING,
            cls.CLIMATE_KEEPER_MODE,
            cls.DRIVER_TEMP_SETTING,
            cls.PASSENGER_TEMP_SETTING,
            cls.FAN_STATUS,
            cls.IS_REAR_DEFROSTER_ON,
            cls.IS_FRONT_DEFROSTER_ON,
        })

    @classmethod
    def door_events(cls) -> frozenset["EventType"]:
        """All event types related to doors, trunk, and frunk."""
        return frozenset({
            cls.DOORS_OPEN,
            cls.DRIVER_FRONT_DOOR_OPEN,
            cls.DRIVER_REAR_DOOR_OPEN,
            cls.PASSENGER_FRONT_DOOR_OPEN,
            cls.PASSENGER_REAR_DOOR_OPEN,
            cls.TRUNK_OPEN,
            cls.FRUNK_OPEN,
        })

    @classmethod
    def window_events(cls) -> frozenset["EventType"]:
        """All event types related to windows."""
        return frozenset({
            cls.WINDOWS_OPEN,
            cls.DRIVER_FRONT_WINDOW_OPEN,
            cls.PASSENGER_FRONT_WINDOW_OPEN,
            cls.DRIVER_REAR_WINDOW_OPEN,
            cls.PASSENGER_REAR_WINDOW_OPEN,
        })

    @classmethod
    def location_events(cls) -> frozenset["EventType"]:
        """All event types related to location and motion."""
        return frozenset({
            cls.LATITUDE,
            cls.LONGITUDE,
            cls.HEADING,
            cls.SPEED,
            cls.ELEVATION,
            cls.ODOMETER,
            cls.SHIFT_STATE,
        })

    @classmethod
    def security_events(cls) -> frozenset["EventType"]:
        """All event types related to security."""
        return frozenset({
            cls.LOCKED,
            cls.SENTRY_MODE,
        })


@dataclass
class TeslaEvent:
    """
    Represents a single state-change notification from TeslaMate via MQTT.

    Instances are created by :class:`~tesla.mqtt_client.TeslaMQTTClient` and
    delivered to every registered callback.

    Attributes
    ----------
    event_type:
        Categorised event kind (see :class:`EventType`).
    topic_key:
        Raw MQTT topic suffix, e.g. ``"battery_level"``.
    old_value:
        The previous Python-typed value stored in :class:`~tesla.models.state.TeslaState`
        before this message arrived.  ``None`` on first receipt.
    new_value:
        The new Python-typed value after parsing the MQTT payload.
    raw_payload:
        The original UTF-8 string published by TeslaMate.
    timestamp:
        Wall-clock time the MQTT message was received.
    state:
        A snapshot of the full :class:`~tesla.models.state.TeslaState` *after*
        this update has been applied.  Useful for callbacks that need the
        complete picture alongside the delta.
    is_initial:
        ``True`` when this is the first time this topic has been received
        (i.e. a retained message on connect, not a live change).
    """

    event_type: EventType
    topic_key: str
    old_value: Any
    new_value: Any
    raw_payload: str
    timestamp: datetime
    state: "TeslaState"
    is_initial: bool = False

    # ------------------------------------------------------------------ #
    # Convenience properties
    # ------------------------------------------------------------------ #

    @property
    def changed(self) -> bool:
        """True when the value actually changed (not just a repeated retained message)."""
        return self.old_value != self.new_value

    @property
    def is_charging_event(self) -> bool:
        """True when this event is related to charging."""
        return self.event_type in EventType.charging_events()

    @property
    def is_battery_event(self) -> bool:
        """True when this event is related to battery state."""
        return self.event_type in EventType.battery_events()

    @property
    def is_climate_event(self) -> bool:
        """True when this event is related to climate / temperature."""
        return self.event_type in EventType.climate_events()

    @property
    def is_door_event(self) -> bool:
        """True when this event is related to doors, trunk, or frunk."""
        return self.event_type in EventType.door_events()

    @property
    def is_window_event(self) -> bool:
        """True when this event is related to windows."""
        return self.event_type in EventType.window_events()

    @property
    def is_location_event(self) -> bool:
        """True when this event is related to location or motion."""
        return self.event_type in EventType.location_events()

    @property
    def is_security_event(self) -> bool:
        """True when this event is related to security."""
        return self.event_type in EventType.security_events()

    def __repr__(self) -> str:
        change = f"{self.old_value!r} → {self.new_value!r}" if self.changed else repr(self.new_value)
        flag = " [initial]" if self.is_initial else ""
        return (
            f"TeslaEvent({self.event_type.name}{flag} "
            f"@ {self.timestamp.strftime('%H:%M:%S')}: {change})"
        )
