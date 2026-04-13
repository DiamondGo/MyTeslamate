"""
TeslaMQTTClient – MQTT listener that keeps TeslaState up-to-date and fires
event callbacks whenever a topic value changes.

Usage example::

    from tesla import TeslaMQTTClient, TeslaEvent, EventType

    def on_plugged_in(event: TeslaEvent):
        print(f"Plug state changed: {event.new_value}")

    client = TeslaMQTTClient(broker="localhost", port=1883, car_id=1)
    client.on(EventType.PLUGGED_IN, on_plugged_in)
    client.on_any(lambda e: print(e))   # catch-all

    client.start()          # non-blocking; runs MQTT loop in background thread
    # ... do other work ...
    client.stop()

Or use as a context manager::

    with TeslaMQTTClient() as client:
        client.on(EventType.BATTERY_LEVEL, lambda e: print(e.new_value))
        import time; time.sleep(30)
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from datetime import datetime
from typing import Callable, Dict, List, Optional, Set

import paho.mqtt.client as mqtt

from tesla.models.event import EventType, TeslaEvent
from tesla.models.state import TeslaState

logger = logging.getLogger(__name__)

# Type alias for event callbacks
EventCallback = Callable[[TeslaEvent], None]


class TeslaMQTTClient:
    """
    Connects to the TeslaMate Mosquitto broker, subscribes to all vehicle
    topics, and maintains a live :class:`~tesla.models.state.TeslaState`.

    Every incoming MQTT message is:
      1. Parsed and applied to the internal :attr:`state`.
      2. Wrapped in a :class:`~tesla.models.event.TeslaEvent`.
      3. Dispatched to all matching callbacks registered via :meth:`on` /
         :meth:`on_any`.

    Parameters
    ----------
    broker:
        Hostname or IP of the Mosquitto broker (default ``"localhost"``).
    port:
        TCP port (default ``1883``).
    car_id:
        TeslaMate vehicle ID (default ``1``).
    namespace:
        TeslaMate MQTT namespace as configured in docker-compose
        (``MQTT_NAMESPACE``, default ``"teslamate"``).
    client_id:
        MQTT client identifier string.
    keepalive:
        MQTT keepalive interval in seconds.
    reconnect_delay:
        Seconds to wait before attempting reconnection after a disconnect.
    emit_unchanged:
        When ``True``, callbacks are fired even when the value has not
        changed (e.g. repeated retained messages).  Default ``False``.
    """

    def __init__(
        self,
        broker: str = "localhost",
        port: int = 1883,
        car_id: int = 1,
        namespace: str = "teslamate",
        client_id: str = "tesla_mqtt_client",
        keepalive: int = 60,
        reconnect_delay: float = 5.0,
        emit_unchanged: bool = False,
    ) -> None:
        self.broker = broker
        self.port = port
        self.car_id = car_id
        self.namespace = namespace
        self.keepalive = keepalive
        self.reconnect_delay = reconnect_delay
        self.emit_unchanged = emit_unchanged

        # The live vehicle state – updated on every incoming message.
        self.state: TeslaState = TeslaState()

        # Track which topic keys have been seen at least once (for is_initial).
        self._seen_topics: Set[str] = set()

        # Callback registry: EventType → list of callbacks.
        self._callbacks: Dict[EventType, List[EventCallback]] = defaultdict(list)
        # Catch-all callbacks (receive every event).
        self._any_callbacks: List[EventCallback] = []

        # Threading
        self._lock = threading.Lock()
        self._running = False

        # Build the MQTT topic to subscribe to.
        self._topic = f"teslamate/{namespace}/cars/{car_id}/#"

        # Paho client (VERSION2 API for modern callback signatures).
        self._mqtt = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id,
        )
        self._mqtt.on_connect = self._on_connect
        self._mqtt.on_message = self._on_message
        self._mqtt.on_disconnect = self._on_disconnect

    # ------------------------------------------------------------------ #
    # Public API – lifecycle
    # ------------------------------------------------------------------ #

    def start(self) -> None:
        """
        Connect to the broker and start the background MQTT loop thread.

        Returns immediately; the MQTT loop runs in a daemon thread.
        Call :meth:`stop` to disconnect cleanly.
        """
        if self._running:
            logger.warning("TeslaMQTTClient.start() called while already running.")
            return

        logger.info("Connecting to MQTT broker %s:%d …", self.broker, self.port)
        self._mqtt.connect(self.broker, self.port, keepalive=self.keepalive)
        self._mqtt.loop_start()
        self._running = True
        logger.info("MQTT loop started (background thread).")

    def stop(self) -> None:
        """Disconnect from the broker and stop the background loop thread."""
        if not self._running:
            return
        logger.info("Stopping TeslaMQTTClient …")
        self._mqtt.loop_stop()
        self._mqtt.disconnect()
        self._running = False
        logger.info("TeslaMQTTClient stopped.")

    def wait_for_initial_state(self, timeout: float = 10.0) -> bool:
        """
        Block until at least one MQTT message has been received (i.e. the
        broker has delivered retained messages) or *timeout* seconds elapse.

        Returns
        -------
        bool
            ``True`` if at least one message was received within *timeout*.
        """
        deadline = datetime.now().timestamp() + timeout
        while datetime.now().timestamp() < deadline:
            with self._lock:
                if self._seen_topics:
                    return True
            threading.Event().wait(0.1)
        return False

    # ------------------------------------------------------------------ #
    # Public API – callback registration
    # ------------------------------------------------------------------ #

    def on(self, event_type: EventType, callback: EventCallback) -> "TeslaMQTTClient":
        """
        Register *callback* to be called whenever *event_type* is received.

        Multiple callbacks can be registered for the same event type.
        Returns ``self`` for chaining.

        Parameters
        ----------
        event_type:
            The :class:`~tesla.models.event.EventType` to listen for.
        callback:
            A callable that accepts a single :class:`~tesla.models.event.TeslaEvent`
            argument.

        Example
        -------
        ::

            client.on(EventType.PLUGGED_IN, lambda e: print("Plugged in:", e.new_value))
        """
        self._callbacks[event_type].append(callback)
        return self

    def on_any(self, callback: EventCallback) -> "TeslaMQTTClient":
        """
        Register *callback* to be called for **every** incoming MQTT event,
        regardless of type.  Returns ``self`` for chaining.

        Example
        -------
        ::

            client.on_any(lambda e: print(e))
        """
        self._any_callbacks.append(callback)
        return self

    def off(self, event_type: EventType, callback: EventCallback) -> None:
        """Remove a previously registered callback for *event_type*."""
        try:
            self._callbacks[event_type].remove(callback)
        except ValueError:
            pass

    def off_any(self, callback: EventCallback) -> None:
        """Remove a previously registered catch-all callback."""
        try:
            self._any_callbacks.remove(callback)
        except ValueError:
            pass

    # ------------------------------------------------------------------ #
    # Public API – convenience filters
    # ------------------------------------------------------------------ #

    def on_charging_change(self, callback: EventCallback) -> "TeslaMQTTClient":
        """Register *callback* for all charging-related events."""
        for et in EventType.charging_events():
            self.on(et, callback)
        return self

    def on_climate_change(self, callback: EventCallback) -> "TeslaMQTTClient":
        """Register *callback* for all climate-related events."""
        for et in EventType.climate_events():
            self.on(et, callback)
        return self

    def on_door_change(self, callback: EventCallback) -> "TeslaMQTTClient":
        """Register *callback* for all door/trunk/frunk events."""
        for et in EventType.door_events():
            self.on(et, callback)
        return self

    def on_window_change(self, callback: EventCallback) -> "TeslaMQTTClient":
        """Register *callback* for all window events."""
        for et in EventType.window_events():
            self.on(et, callback)
        return self

    def on_location_change(self, callback: EventCallback) -> "TeslaMQTTClient":
        """Register *callback* for all location/motion events."""
        for et in EventType.location_events():
            self.on(et, callback)
        return self

    def on_security_change(self, callback: EventCallback) -> "TeslaMQTTClient":
        """Register *callback* for all security events."""
        for et in EventType.security_events():
            self.on(et, callback)
        return self

    # ------------------------------------------------------------------ #
    # Context manager support
    # ------------------------------------------------------------------ #

    def __enter__(self) -> "TeslaMQTTClient":
        self.start()
        return self

    def __exit__(self, *_) -> None:
        self.stop()

    # ------------------------------------------------------------------ #
    # Internal – Paho callbacks
    # ------------------------------------------------------------------ #

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        """Called by Paho when the connection is established."""
        if reason_code == 0:
            logger.info(
                "Connected to MQTT broker %s:%d – subscribing to %s",
                self.broker, self.port, self._topic,
            )
            client.subscribe(self._topic)
        else:
            logger.error("MQTT connection failed, reason_code=%s", reason_code)

    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        """Called by Paho on disconnect."""
        if reason_code != 0:
            logger.warning(
                "Unexpected MQTT disconnect (reason_code=%s). "
                "Paho will attempt automatic reconnection.",
                reason_code,
            )
        else:
            logger.info("MQTT disconnected cleanly.")

    def _on_message(self, client, userdata, msg: mqtt.MQTTMessage):
        """
        Called by Paho for every incoming message.

        Thread-safe: acquires ``_lock`` while mutating shared state.
        """
        try:
            topic: str = msg.topic
            raw_payload: str = msg.payload.decode("utf-8", errors="replace").strip()
            received_at = datetime.now()

            # Extract the topic key (last path segment).
            topic_key = topic.split("/")[-1]

            with self._lock:
                # Capture old value before update.
                old_value = getattr(self.state, topic_key, None)
                is_initial = topic_key not in self._seen_topics

                # Apply to state (returns False if topic is unknown).
                known = self.state.apply_mqtt(topic_key, raw_payload)
                self._seen_topics.add(topic_key)

                # Read back the parsed new value.
                new_value = getattr(self.state, topic_key, raw_payload)

                # Take a snapshot for the event (outside the lock would be
                # a TOCTOU race, so we snapshot while holding the lock).
                state_snapshot = self.state.snapshot()

            # Resolve event type.
            event_type = EventType.from_topic(topic_key)

            # Build the event.
            event = TeslaEvent(
                event_type=event_type,
                topic_key=topic_key,
                old_value=old_value,
                new_value=new_value,
                raw_payload=raw_payload,
                timestamp=received_at,
                state=state_snapshot,
                is_initial=is_initial,
            )

            # Skip dispatch if value unchanged and emit_unchanged is False.
            if not self.emit_unchanged and not event.changed and not is_initial:
                logger.debug("Skipping unchanged event: %s", event)
                return

            logger.debug("Event: %s", event)

            # Dispatch to specific callbacks.
            self._dispatch(event)

        except Exception:
            logger.exception("Error processing MQTT message on topic %s", msg.topic)

    def _dispatch(self, event: TeslaEvent) -> None:
        """Fire all callbacks registered for this event type, then catch-alls."""
        # Specific callbacks.
        for cb in list(self._callbacks.get(event.event_type, [])):
            self._safe_call(cb, event)

        # Catch-all callbacks.
        for cb in list(self._any_callbacks):
            self._safe_call(cb, event)

    @staticmethod
    def _safe_call(callback: EventCallback, event: TeslaEvent) -> None:
        """Call *callback* with *event*, logging any exception without re-raising."""
        try:
            callback(event)
        except Exception:
            logger.exception(
                "Unhandled exception in event callback %s for event %s",
                callback, event,
            )

    # ------------------------------------------------------------------ #
    # Repr
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        status = "running" if self._running else "stopped"
        return (
            f"TeslaMQTTClient(broker={self.broker!r}, port={self.port}, "
            f"car_id={self.car_id}, status={status!r})"
        )
