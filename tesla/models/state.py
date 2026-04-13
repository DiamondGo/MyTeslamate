"""
TeslaState – a snapshot of the full vehicle state.

All fields are Optional so the object can be constructed incrementally as
MQTT retained messages arrive.  Every field maps 1-to-1 to a TeslaMate MQTT
topic suffix (the last path segment after ``teslamate/<ns>/cars/<id>/``).

Field types follow TeslaMate's published value format:
  - bool fields  → Python bool  (TeslaMate publishes "true" / "false")
  - numeric      → int or float
  - string       → str
  - datetime     → datetime (ISO-8601 strings are parsed automatically)

The ``updated_at`` field records the wall-clock time of the most recent
field update so callers can detect stale state.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, asdict
from datetime import datetime
from typing import Optional
import copy


@dataclass
class TeslaState:
    """Complete snapshot of a Tesla vehicle as reported by TeslaMate via MQTT."""

    # ------------------------------------------------------------------ #
    # Identity / health
    # ------------------------------------------------------------------ #
    display_name: Optional[str] = None
    """Human-readable vehicle name (e.g. "My Model 3")."""

    state: Optional[str] = None
    """High-level vehicle state: 'online', 'asleep', 'offline', 'charging', 'updating'."""

    healthy: Optional[bool] = None
    """True when TeslaMate considers the vehicle connection healthy."""

    # ------------------------------------------------------------------ #
    # Battery & charging
    # ------------------------------------------------------------------ #
    battery_level: Optional[int] = None
    """State-of-charge in percent (0–100)."""

    usable_battery_level: Optional[int] = None
    """Usable SoC in percent (may differ from battery_level in cold weather)."""

    charge_limit_soc: Optional[int] = None
    """Charge limit set by the driver (percent)."""

    charge_limit_soc_std: Optional[int] = None
    """Standard charge limit (percent)."""

    charge_limit_soc_min: Optional[int] = None
    """Minimum allowed charge limit (percent)."""

    charge_limit_soc_max: Optional[int] = None
    """Maximum allowed charge limit (percent)."""

    est_battery_range_km: Optional[float] = None
    """Estimated remaining range in kilometres."""

    rated_battery_range_km: Optional[float] = None
    """Rated remaining range in kilometres."""

    ideal_battery_range_km: Optional[float] = None
    """Ideal remaining range in kilometres."""

    plugged_in: Optional[bool] = None
    """True when the charge cable is connected."""

    charge_port_door_open: Optional[bool] = None
    """True when the charge port door is open."""

    charging_state: Optional[str] = None
    """Charging state string: 'Charging', 'Complete', 'Disconnected', 'Stopped', 'NoPower'."""

    charger_power: Optional[int] = None
    """Current charger power in kW."""

    charger_voltage: Optional[int] = None
    """Charger voltage in V."""

    charger_actual_current: Optional[int] = None
    """Actual charging current in A."""

    charger_phases: Optional[int] = None
    """Number of charger phases (1 or 3)."""

    charge_energy_added: Optional[float] = None
    """Energy added in the current charging session (kWh)."""

    charge_limit_soc_reached: Optional[bool] = None
    """True when the charge limit SoC has been reached."""

    scheduled_charging_start_time: Optional[datetime] = None
    """Scheduled charging start time (if set)."""

    time_to_full_charge: Optional[float] = None
    """Estimated time to full charge in hours."""

    # ------------------------------------------------------------------ #
    # Climate / temperature
    # ------------------------------------------------------------------ #
    inside_temp: Optional[float] = None
    """Cabin temperature in °C."""

    outside_temp: Optional[float] = None
    """Ambient temperature in °C."""

    is_climate_on: Optional[bool] = None
    """True when the climate system is active."""

    is_preconditioning: Optional[bool] = None
    """True when the battery is being pre-conditioned."""

    climate_keeper_mode: Optional[str] = None
    """Climate keeper mode: 'off', 'on', 'dog', 'camp'."""

    driver_temp_setting: Optional[float] = None
    """Driver-side temperature setting in °C."""

    passenger_temp_setting: Optional[float] = None
    """Passenger-side temperature setting in °C."""

    fan_status: Optional[int] = None
    """Fan speed level (0 = off)."""

    is_rear_defroster_on: Optional[bool] = None
    """True when the rear defroster is active."""

    is_front_defroster_on: Optional[bool] = None
    """True when the front defroster is active."""

    # ------------------------------------------------------------------ #
    # Ventilation / windows
    # ------------------------------------------------------------------ #
    windows_open: Optional[bool] = None
    """True when any window is open."""

    driver_front_window_open: Optional[bool] = None
    passenger_front_window_open: Optional[bool] = None
    driver_rear_window_open: Optional[bool] = None
    passenger_rear_window_open: Optional[bool] = None

    # ------------------------------------------------------------------ #
    # Doors & trunk
    # ------------------------------------------------------------------ #
    doors_open: Optional[bool] = None
    """True when any door is open."""

    driver_front_door_open: Optional[bool] = None
    driver_rear_door_open: Optional[bool] = None
    passenger_front_door_open: Optional[bool] = None
    passenger_rear_door_open: Optional[bool] = None

    trunk_open: Optional[bool] = None
    """True when the rear trunk is open."""

    frunk_open: Optional[bool] = None
    """True when the front trunk (frunk) is open."""

    # ------------------------------------------------------------------ #
    # Security
    # ------------------------------------------------------------------ #
    locked: Optional[bool] = None
    """True when the vehicle is locked."""

    sentry_mode: Optional[bool] = None
    """True when Sentry Mode is active."""

    # ------------------------------------------------------------------ #
    # Location & motion
    # ------------------------------------------------------------------ #
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    heading: Optional[int] = None
    """Compass heading in degrees (0–360)."""

    speed: Optional[int] = None
    """Vehicle speed in km/h."""

    elevation: Optional[int] = None
    """Elevation above sea level in metres."""

    odometer: Optional[float] = None
    """Total odometer reading in km."""

    shift_state: Optional[str] = None
    """Gear selector position: 'P', 'D', 'R', 'N', or None when parked/off."""

    # ------------------------------------------------------------------ #
    # Power & energy
    # ------------------------------------------------------------------ #
    power: Optional[int] = None
    """Instantaneous power in kW (positive = consuming, negative = regenerating)."""

    # ------------------------------------------------------------------ #
    # Accessories & misc
    # ------------------------------------------------------------------ #
    is_user_present: Optional[bool] = None
    """True when a driver is detected in the vehicle."""

    keep_accessory_power_on: Optional[bool] = None
    """True when accessory power (12 V) is kept on while parked."""

    center_display_state: Optional[int] = None
    """Center display state (0 = off, 2 = on, 3 = charging screen, etc.)."""

    # ------------------------------------------------------------------ #
    # Tyre pressure monitoring (TPMS)
    # ------------------------------------------------------------------ #
    tpms_pressure_fl: Optional[float] = None
    """Front-left tyre pressure in bar."""

    tpms_pressure_fr: Optional[float] = None
    """Front-right tyre pressure in bar."""

    tpms_pressure_rl: Optional[float] = None
    """Rear-left tyre pressure in bar."""

    tpms_pressure_rr: Optional[float] = None
    """Rear-right tyre pressure in bar."""

    tpms_soft_warning_fl: Optional[bool] = None
    """True when front-left tyre pressure is below soft-warning threshold."""

    tpms_soft_warning_fr: Optional[bool] = None
    """True when front-right tyre pressure is below soft-warning threshold."""

    tpms_soft_warning_rl: Optional[bool] = None
    """True when rear-left tyre pressure is below soft-warning threshold."""

    tpms_soft_warning_rr: Optional[bool] = None
    """True when rear-right tyre pressure is below soft-warning threshold."""

    # ------------------------------------------------------------------ #
    # Active route / navigation
    # ------------------------------------------------------------------ #
    active_route: Optional[str] = None
    """JSON blob describing the active navigation route (or error string)."""

    active_route_destination: Optional[str] = None
    """Destination name of the active route ('nil' when none)."""

    active_route_latitude: Optional[str] = None
    """Latitude of the active route destination ('nil' when none)."""

    active_route_longitude: Optional[str] = None
    """Longitude of the active route destination ('nil' when none)."""

    location: Optional[str] = None
    """JSON blob with current latitude/longitude."""

    # ------------------------------------------------------------------ #
    # Charging current limits
    # ------------------------------------------------------------------ #
    charge_current_request: Optional[int] = None
    """Requested charging current in A."""

    charge_current_request_max: Optional[int] = None
    """Maximum allowed charging current in A."""

    # ------------------------------------------------------------------ #
    # Vehicle identity / trim
    # ------------------------------------------------------------------ #
    model: Optional[str] = None
    """Vehicle model letter, e.g. 'Y', '3', 'S', 'X'."""

    trim_badging: Optional[str] = None
    """Trim badge string, e.g. '74D', 'P100D'."""

    exterior_color: Optional[str] = None
    """Exterior colour name, e.g. 'StealthGrey'."""

    spoiler_type: Optional[str] = None
    """Spoiler type string, e.g. 'None', 'Passive'."""

    wheel_type: Optional[str] = None
    """Wheel type string, e.g. 'Crossflow19'."""

    since: Optional[str] = None
    """ISO-8601 timestamp of when the current vehicle state began."""

    # ------------------------------------------------------------------ #
    # Software
    # ------------------------------------------------------------------ #
    version: Optional[str] = None
    """Current firmware version string."""

    update_available: Optional[bool] = None
    """True when a software update is available."""

    update_version: Optional[str] = None
    """Version string of the pending update."""

    # ------------------------------------------------------------------ #
    # Internal bookkeeping (not from MQTT)
    # ------------------------------------------------------------------ #
    updated_at: Optional[datetime] = field(default=None, repr=False)
    """Wall-clock time of the most recent field update."""

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def apply_mqtt(self, topic_key: str, raw_value: str) -> bool:
        """
        Parse *raw_value* and store it in the matching field.

        Parameters
        ----------
        topic_key:
            The last segment of the MQTT topic path, e.g. ``"battery_level"``.
        raw_value:
            The raw UTF-8 payload string published by TeslaMate.

        Returns
        -------
        bool
            ``True`` if the field existed and was updated, ``False`` if the
            topic is unknown (the field is silently ignored).
        """
        # Normalise key: TeslaMate uses snake_case which matches our field names.
        attr = topic_key.lower()

        # Check the field exists on this dataclass.
        known = {f.name for f in fields(self)}
        if attr not in known or attr == "updated_at":
            return False

        # Determine the declared type and coerce accordingly.
        f_type = self.__dataclass_fields__[attr].type  # type: ignore[attr-defined]
        parsed = _coerce(raw_value, f_type)
        setattr(self, attr, parsed)
        self.updated_at = datetime.now()
        return True

    def as_dict(self) -> dict:
        """Return a plain dict representation (datetime objects become ISO strings)."""
        result = {}
        for f in fields(self):
            val = getattr(self, f.name)
            if isinstance(val, datetime):
                result[f.name] = val.isoformat()
            else:
                result[f.name] = val
        return result

    def snapshot(self) -> "TeslaState":
        """Return a deep copy of the current state."""
        return copy.deepcopy(self)

    def __repr__(self) -> str:
        # Only show non-None fields for readability.
        parts = []
        for f in fields(self):
            val = getattr(self, f.name)
            if val is not None:
                parts.append(f"{f.name}={val!r}")
        return f"TeslaState({', '.join(parts)})"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_BOOL_TRUE = {"true", "1", "yes", "on"}
_BOOL_FALSE = {"false", "0", "no", "off"}


def _coerce(raw: str, type_hint: str):
    """
    Convert a raw MQTT string payload to the Python type declared in the
    dataclass field annotation.

    Supported type hints (as strings, because ``from __future__ import annotations``
    makes all annotations lazy strings):
      ``Optional[bool]``, ``Optional[int]``, ``Optional[float]``,
      ``Optional[str]``, ``Optional[datetime]``
    """
    if raw is None or raw == "":
        return None

    raw = raw.strip()

    if "bool" in type_hint:
        lower = raw.lower()
        if lower in _BOOL_TRUE:
            return True
        if lower in _BOOL_FALSE:
            return False
        return None

    if "datetime" in type_hint:
        try:
            # TeslaMate publishes ISO-8601 strings, e.g. "2024-01-15T08:30:00Z"
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None

    if "float" in type_hint:
        try:
            return float(raw)
        except ValueError:
            return None

    if "int" in type_hint:
        try:
            # Some values arrive as "3.0" – truncate gracefully.
            return int(float(raw))
        except ValueError:
            return None

    # Default: keep as string.
    return raw
