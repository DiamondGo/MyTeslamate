#!/usr/bin/env python3
"""
demo.py – demonstrates the tesla package: TeslaState, TeslaEvent, TeslaMQTTClient.

Run with:
    python demo.py

The script connects to the local TeslaMate Mosquitto broker (localhost:1883),
collects the initial retained state, then listens for live changes for 60 seconds.

Press Ctrl+C to exit early.
"""

import logging
import time
import sys

# Configure logging so we can see debug output from the library.
logging.basicConfig(
    level=logging.WARNING,          # set to DEBUG to see every MQTT message
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

from tesla import TeslaMQTTClient, TeslaEvent, EventType

# ---------------------------------------------------------------------------
# Callback definitions
# ---------------------------------------------------------------------------

def on_any_event(event: TeslaEvent) -> None:
    """Catch-all: print every event that carries a changed value."""
    if event.is_initial:
        # Initial retained messages – show them as "current state" lines.
        print(f"  [INIT] {event.topic_key:40s} = {event.new_value}")
    else:
        # Live change.
        print(
            f"  [CHANGE] {event.event_type.name:35s} "
            f"{event.old_value!r:20} → {event.new_value!r}"
        )


def on_plugged_in(event: TeslaEvent) -> None:
    """React specifically to charge-cable plug/unplug events."""
    if event.is_initial:
        return  # already shown by on_any_event
    if event.new_value:
        print("\n  ⚡ Charge cable CONNECTED")
    else:
        print("\n  🔌 Charge cable DISCONNECTED")


def on_climate(event: TeslaEvent) -> None:
    """React to any climate-related change."""
    if event.is_initial:
        return
    print(
        f"\n  🌡️  Climate event [{event.event_type.name}]: "
        f"{event.old_value} → {event.new_value}"
    )


def on_door(event: TeslaEvent) -> None:
    """React to any door/trunk/frunk change."""
    if event.is_initial:
        return
    label = event.event_type.name.replace("_", " ").title()
    state_str = "OPEN" if event.new_value else "CLOSED"
    print(f"\n  🚪 {label}: {state_str}")


def on_security(event: TeslaEvent) -> None:
    """React to lock / sentry mode changes."""
    if event.is_initial:
        return
    if event.event_type == EventType.LOCKED:
        print(f"\n  {'🔒 LOCKED' if event.new_value else '🔓 UNLOCKED'}")
    elif event.event_type == EventType.SENTRY_MODE:
        print(f"\n  {'👁️  Sentry ON' if event.new_value else '👁️  Sentry OFF'}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 70)
    print("  Tesla MQTT Demo")
    print("=" * 70)
    print("  Connecting to localhost:1883 …")
    print()

    client = TeslaMQTTClient(
        broker="localhost",
        port=1883,
        car_id=1,
        namespace="teslamate",
        client_id="tesla_demo",
        emit_unchanged=False,   # only fire callbacks when value actually changes
    )

    # Register callbacks.
    client.on_any(on_any_event)
    client.on(EventType.PLUGGED_IN, on_plugged_in)
    client.on_climate_change(on_climate)
    client.on_door_change(on_door)
    client.on_security_change(on_security)

    try:
        client.start()

        # Wait up to 5 s for the broker to deliver retained messages.
        print("  Waiting for initial retained state (up to 5 s) …")
        print()
        print("  ── Initial State ──────────────────────────────────────────────")
        got_state = client.wait_for_initial_state(timeout=5.0)
        time.sleep(3)   # give retained messages a moment to all arrive
        print("  ───────────────────────────────────────────────────────────────")
        print()

        if not got_state:
            print("  ⚠️  No MQTT messages received within 5 s.")
            print("     The vehicle may be asleep or TeslaMate is not publishing.")
        else:
            # Print a structured summary of the current state.
            s = client.state
            print("  ── Structured TeslaState Summary ──────────────────────────────")
            print(f"  Name          : {s.display_name}")
            print(f"  State         : {s.state}")
            print(f"  Battery       : {s.battery_level}%  (usable: {s.usable_battery_level}%)")
            print(f"  Range (rated) : {s.rated_battery_range_km} km")
            print(f"  Plugged in    : {s.plugged_in}")
            print(f"  Charging state: {s.charging_state}")
            print(f"  Charger power : {s.charger_power} kW")
            print(f"  Inside temp   : {s.inside_temp} °C")
            print(f"  Outside temp  : {s.outside_temp} °C")
            print(f"  Climate on    : {s.is_climate_on}")
            print(f"  Preconditioning: {s.is_preconditioning}")
            print(f"  Locked        : {s.locked}")
            print(f"  Sentry mode   : {s.sentry_mode}")
            print(f"  Doors open    : {s.doors_open}")
            print(f"  Windows open  : {s.windows_open}")
            print(f"  Speed         : {s.speed} km/h")
            print(f"  Location      : {s.latitude}, {s.longitude}")
            print(f"  Last updated  : {s.updated_at}")
            print("  ───────────────────────────────────────────────────────────────")
            print()

        print("  Now listening for live changes … (Ctrl+C to exit)")
        print()

        # Keep running until interrupted.
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print()
        print("=" * 70)
        print("  Interrupted – stopping.")
        print("=" * 70)
    finally:
        client.stop()


if __name__ == "__main__":
    main()
