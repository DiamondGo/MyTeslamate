"""
AutomationApp – wires Monitor, Scheduler, and Controller into a single application.

Usage::

    from tesla.app import AutomationApp

    app = AutomationApp(rules_path="rules.yaml")
    app.run()   # blocking – press Ctrl+C to stop

Or with dry-run mode (no API calls)::

    app = AutomationApp(rules_path="rules.yaml", dry_run=True)
    app.run()
"""

from __future__ import annotations

import logging
import signal
import time
from typing import Optional

from tesla.controller import TeslaController
from tesla.models.state import TeslaState
from tesla.mqtt_client import TeslaMQTTClient
from tesla.scheduler.engine import RuleEngine
from tesla.scheduler.loader import RuleLoader

logger = logging.getLogger(__name__)


class AutomationApp:
    """
    Main application that connects Monitor → Scheduler → Controller.

    Parameters
    ----------
    mqtt_broker:
        Hostname or IP of the Mosquitto broker.
    mqtt_port:
        TCP port of the Mosquitto broker.
    car_id:
        TeslaMate vehicle ID.
    mqtt_namespace:
        TeslaMate MQTT namespace (``MQTT_NAMESPACE`` in docker-compose).
    tesla_email:
        Tesla account email for Fleet API authentication via teslapy.
    rules_path:
        Path to the YAML rules file.
    cache_path:
        Path to the teslapy OAuth token cache.  Defaults to
        ``private/cache.json``.
    dry_run:
        When ``True``, the rule engine evaluates conditions but does NOT
        send any commands to the vehicle.
    initial_state_timeout:
        Seconds to wait for the first MQTT retained messages before
        starting the automation loop.
    """

    def __init__(
        self,
        mqtt_broker: str = "localhost",
        mqtt_port: int = 1883,
        car_id: int = 1,
        mqtt_namespace: str = "teslamate",
        tesla_email: str = "",
        rules_path: str = "rules.yaml",
        cache_path: Optional[str] = None,
        dry_run: bool = False,
        initial_state_timeout: float = 10.0,
    ) -> None:
        self.dry_run = dry_run
        self.initial_state_timeout = initial_state_timeout

        # ── Monitor ──────────────────────────────────────────────────── #
        self.mqtt_client = TeslaMQTTClient(
            broker=mqtt_broker,
            port=mqtt_port,
            car_id=car_id,
            namespace=mqtt_namespace,
            client_id="tesla_automation_app",
        )

        # ── Controller ───────────────────────────────────────────────── #
        ctrl_kwargs = dict(
            email=tesla_email,
            state=self.mqtt_client.state,
        )
        if cache_path:
            ctrl_kwargs["cache_path"] = cache_path
        self.controller = TeslaController(**ctrl_kwargs)

        # ── Scheduler ────────────────────────────────────────────────── #
        rules = RuleLoader(strict=False).load(rules_path)
        self.engine = RuleEngine(
            controller=self.controller,
            rules=rules,
            dry_run=dry_run,
        )

        # Wire: every MQTT event is evaluated by the rule engine.
        self.mqtt_client.on_any(self.engine.evaluate)

        self._running = False

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def run(self) -> None:
        """
        Start the MQTT client and block until interrupted.

        Handles SIGINT / SIGTERM for clean shutdown.
        """
        self._setup_signal_handlers()

        logger.info("=" * 60)
        logger.info("Tesla Automation System starting …")
        logger.info("  Rules loaded : %d (%d enabled)",
                    len(self.engine.rules),
                    sum(1 for r in self.engine.rules if r.enabled))
        if self.dry_run:
            logger.info("  Mode         : DRY-RUN (no API calls)")
        logger.info("=" * 60)

        with self.mqtt_client:
            logger.info("Waiting for initial vehicle state (timeout=%.0fs) …",
                        self.initial_state_timeout)
            got_state = self.mqtt_client.wait_for_initial_state(
                timeout=self.initial_state_timeout
            )
            if got_state:
                s = self.mqtt_client.state
                logger.info(
                    "Initial state received: %s | battery=%s%% | "
                    "plugged_in=%s | inside_temp=%s°C | geofence=%s",
                    s.state, s.battery_level, s.plugged_in,
                    s.inside_temp, s.geofence,
                )
            else:
                logger.warning(
                    "No MQTT messages received within %.0fs. "
                    "Vehicle may be asleep. Automation will activate when "
                    "TeslaMate publishes updates.",
                    self.initial_state_timeout,
                )

            logger.info("Automation loop running. Press Ctrl+C to stop.")
            self._running = True
            try:
                while self._running:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass

        logger.info("Tesla Automation System stopped.")

    def stop(self) -> None:
        """Signal the run loop to exit cleanly."""
        self._running = False

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #

    def _setup_signal_handlers(self) -> None:
        """Register SIGINT / SIGTERM handlers for clean shutdown."""
        def _handler(signum, frame):
            logger.info("Received signal %d – shutting down …", signum)
            self.stop()

        signal.signal(signal.SIGINT, _handler)
        signal.signal(signal.SIGTERM, _handler)

    def __repr__(self) -> str:
        mode = " [DRY-RUN]" if self.dry_run else ""
        return (
            f"AutomationApp(broker={self.mqtt_client.broker!r}, "
            f"rules={len(self.engine.rules)}{mode})"
        )
