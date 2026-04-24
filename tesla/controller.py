"""
TeslaController – sends commands to the Tesla vehicle via Tesla Fleet API.

Uses the ``teslapy`` library for OAuth token management and API calls.
The token cache is stored in ``private/cache.json`` (gitignored).

Usage example::

    from tesla import TeslaController, TeslaState

    state = TeslaState()   # or the live state from TeslaMQTTClient
    ctrl = TeslaController(email="you@example.com", state=state)

    ctrl.start_climate()
    ctrl.set_temperature(driver_temp=22.0)
    ctrl.set_accessory_power(on=True)

All public methods return ``True`` on success, ``False`` on failure.
Failures are logged at ERROR level but never re-raised, so a failed
command does not crash the automation loop.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import teslapy

from tesla.models.state import TeslaState

logger = logging.getLogger(__name__)

# Path to the teslapy OAuth token cache (gitignored).
_DEFAULT_CACHE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "private", "cache.json"
)


class TeslaController:
    """
    Sends commands to the Tesla vehicle via Tesla Fleet API using teslapy.

    Parameters
    ----------
    email:
        Tesla account email address used for OAuth authentication.
    state:
        Reference to the live :class:`~tesla.models.state.TeslaState`.
        Used for idempotency checks (e.g. skip ``start_climate`` if
        ``is_climate_on`` is already ``True``).
    cache_path:
        Path to the teslapy token cache file.  Defaults to
        ``private/cache.json`` relative to the project root.
    car_index:
        Index of the vehicle in the Tesla account's vehicle list (0-based).
        Defaults to ``0`` (first vehicle).
    """

    def __init__(
        self,
        email: str,
        state: TeslaState,
        cache_path: str = _DEFAULT_CACHE_PATH,
        car_index: int = 0,
    ) -> None:
        self.email = email
        self.state = state
        self.cache_path = cache_path
        self.car_index = car_index

        # Lazily initialised – created on first command call.
        self._tesla: Optional[teslapy.Tesla] = None
        self._vehicle: Optional[teslapy.Vehicle] = None

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _get_vehicle(self) -> Optional[teslapy.Vehicle]:
        """Return the cached vehicle object, initialising teslapy if needed."""
        if self._vehicle is not None:
            return self._vehicle

        try:
            self._tesla = teslapy.Tesla(self.email, cache_file=self.cache_path)
            vehicles = self._tesla.vehicle_list()
            if not vehicles:
                logger.error("No vehicles found in Tesla account for %s", self.email)
                return None
            if self.car_index >= len(vehicles):
                logger.error(
                    "car_index=%d out of range (account has %d vehicle(s))",
                    self.car_index, len(vehicles),
                )
                return None
            self._vehicle = vehicles[self.car_index]
            logger.info(
                "TeslaController initialised for vehicle: %s",
                self._vehicle.get("display_name", "unknown"),
            )
            return self._vehicle
        except Exception:
            logger.exception("Failed to initialise teslapy / fetch vehicle list")
            return None

    def _send_command(self, command: str, **kwargs) -> bool:
        """
        Send a raw command to the vehicle, waking it up first if needed.

        Parameters
        ----------
        command:
            teslapy command name, e.g. ``"CLIMATE_ON"``.
        **kwargs:
            Additional keyword arguments forwarded to ``vehicle.command()``.

        Returns
        -------
        bool
            ``True`` on success, ``False`` on any error.
        """
        vehicle = self._get_vehicle()
        if vehicle is None:
            return False

        try:
            # Wake the vehicle if it is asleep.
            if vehicle.get("state") in ("asleep", "offline"):
                logger.info("Vehicle is %s – waking up before command …", vehicle.get("state"))
                vehicle.sync_wake_up()
                logger.info("Vehicle awake.")

            result = vehicle.command(command, **kwargs)
            logger.info("Command %s succeeded: %s", command, result)
            return True

        except teslapy.VehicleError as exc:
            logger.error("Vehicle rejected command %s: %s", command, exc)
            return False
        except Exception:
            logger.exception("Unexpected error sending command %s", command)
            return False

    # ------------------------------------------------------------------ #
    # Climate
    # ------------------------------------------------------------------ #

    def start_climate(self) -> bool:
        """Start the HVAC system.

        Skipped (returns ``True``) if climate is already on according to
        the current :attr:`state`.
        """
        if self.state.is_climate_on:
            logger.debug("start_climate: climate already on – skipping.")
            return True
        logger.info("Starting climate …")
        return self._send_command("CLIMATE_ON")

    def stop_climate(self) -> bool:
        """Stop the HVAC system."""
        if self.state.is_climate_on is False:
            logger.debug("stop_climate: climate already off – skipping.")
            return True
        logger.info("Stopping climate …")
        return self._send_command("CLIMATE_OFF")

    def set_temperature(
        self,
        driver_temp: float,
        passenger_temp: Optional[float] = None,
    ) -> bool:
        """Set the driver (and optionally passenger) temperature setpoint.

        Parameters
        ----------
        driver_temp:
            Driver-side temperature in °C.
        passenger_temp:
            Passenger-side temperature in °C.  Defaults to ``driver_temp``
            when not specified.
        """
        if passenger_temp is None:
            passenger_temp = driver_temp
        logger.info(
            "Setting temperature: driver=%.1f°C, passenger=%.1f°C",
            driver_temp, passenger_temp,
        )
        return self._send_command(
            "CHANGE_CLIMATE_TEMPERATURE_SETTING",
            driver_temp=driver_temp,
            passenger_temp=passenger_temp,
        )

    def start_climate_keeper(self, mode: str = "on") -> bool:
        """Enable Climate Keeper mode.

        Parameters
        ----------
        mode:
            One of ``"on"``, ``"dog"``, or ``"camp"``.
        """
        mode_map = {"on": 1, "dog": 2, "camp": 3}
        mode_id = mode_map.get(mode.lower())
        if mode_id is None:
            logger.error("Invalid climate keeper mode %r (must be on/dog/camp)", mode)
            return False
        logger.info("Starting climate keeper mode: %s", mode)
        return self._send_command("SET_CLIMATE_KEEPER_MODE", climate_keeper_mode=mode_id)

    # ------------------------------------------------------------------ #
    # Charging
    # ------------------------------------------------------------------ #

    def start_charging(self) -> bool:
        """Start charging."""
        logger.info("Starting charging …")
        return self._send_command("START_CHARGE")

    def stop_charging(self) -> bool:
        """Stop charging."""
        logger.info("Stopping charging …")
        return self._send_command("STOP_CHARGE")

    def set_charge_limit(self, percent: int) -> bool:
        """Set the charge limit.

        Parameters
        ----------
        percent:
            Target state-of-charge limit (0–100).
        """
        logger.info("Setting charge limit to %d%%", percent)
        return self._send_command("CHANGE_CHARGE_LIMIT", percent=percent)

    def open_charge_port(self) -> bool:
        """Open the charge port door."""
        logger.info("Opening charge port …")
        return self._send_command("CHARGE_PORT_DOOR_OPEN")

    def close_charge_port(self) -> bool:
        """Close the charge port door."""
        logger.info("Closing charge port …")
        return self._send_command("CHARGE_PORT_DOOR_CLOSE")

    # ------------------------------------------------------------------ #
    # Security
    # ------------------------------------------------------------------ #

    def lock(self) -> bool:
        """Lock the vehicle doors."""
        if self.state.locked:
            logger.debug("lock: already locked – skipping.")
            return True
        logger.info("Locking vehicle …")
        return self._send_command("LOCK")

    def unlock(self) -> bool:
        """Unlock the vehicle doors."""
        if self.state.locked is False:
            logger.debug("unlock: already unlocked – skipping.")
            return True
        logger.info("Unlocking vehicle …")
        return self._send_command("UNLOCK")

    def enable_sentry_mode(self) -> bool:
        """Enable Sentry Mode."""
        if self.state.sentry_mode:
            logger.debug("enable_sentry_mode: already enabled – skipping.")
            return True
        logger.info("Enabling Sentry Mode …")
        return self._send_command("SET_SENTRY_MODE", on=True)

    def disable_sentry_mode(self) -> bool:
        """Disable Sentry Mode."""
        if self.state.sentry_mode is False:
            logger.debug("disable_sentry_mode: already disabled – skipping.")
            return True
        logger.info("Disabling Sentry Mode …")
        return self._send_command("SET_SENTRY_MODE", on=False)

    # ------------------------------------------------------------------ #
    # Windows & ventilation
    # ------------------------------------------------------------------ #

    def vent_windows(self) -> bool:
        """Vent all windows slightly open."""
        logger.info("Venting windows …")
        return self._send_command("WINDOW_CONTROL", command="vent", lat=0, lon=0)

    def close_windows(self) -> bool:
        """Close all windows.

        Note: requires the vehicle to be in Park and the driver's window
        must be within a certain range of the closed position.
        """
        logger.info("Closing windows …")
        return self._send_command("WINDOW_CONTROL", command="close", lat=0, lon=0)

    # ------------------------------------------------------------------ #
    # Accessories
    # ------------------------------------------------------------------ #

    def set_accessory_power(self, on: bool) -> bool:
        """Enable or disable the 'Keep Accessory Power On' setting.

        Parameters
        ----------
        on:
            ``True`` to enable accessory power, ``False`` to disable.
        """
        if self.state.keep_accessory_power_on == on:
            logger.debug(
                "set_accessory_power(%s): already in desired state – skipping.", on
            )
            return True
        logger.info("Setting accessory power: %s", "ON" if on else "OFF")
        return self._send_command("REMOTE_BOOMBOX", on=on)

    # ------------------------------------------------------------------ #
    # Wake
    # ------------------------------------------------------------------ #

    def wake_up(self) -> bool:
        """Explicitly wake the vehicle from sleep."""
        vehicle = self._get_vehicle()
        if vehicle is None:
            return False
        try:
            logger.info("Waking vehicle …")
            vehicle.sync_wake_up()
            logger.info("Vehicle awake.")
            return True
        except Exception:
            logger.exception("Failed to wake vehicle")
            return False

    # ------------------------------------------------------------------ #
    # Generic
    # ------------------------------------------------------------------ #

    def execute_command(self, command: str, **kwargs) -> bool:
        """Send an arbitrary teslapy command.

        Parameters
        ----------
        command:
            teslapy command name (e.g. ``"HONK_HORN"``).
        **kwargs:
            Additional parameters forwarded to the command.
        """
        logger.info("Executing command: %s %s", command, kwargs)
        return self._send_command(command, **kwargs)

    # ------------------------------------------------------------------ #
    # Context manager / cleanup
    # ------------------------------------------------------------------ #

    def close(self) -> None:
        """Close the teslapy session and release resources."""
        if self._tesla is not None:
            try:
                self._tesla.close()
            except Exception:
                pass
            self._tesla = None
            self._vehicle = None

    def __enter__(self) -> "TeslaController":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def __repr__(self) -> str:
        vehicle_name = (
            self._vehicle.get("display_name", "?") if self._vehicle else "not connected"
        )
        return f"TeslaController(email={self.email!r}, vehicle={vehicle_name!r})"
