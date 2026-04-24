"""
Configuration file example.

Usage:
1. Copy this file to config.py
2. Fill in your actual values
3. config.py is gitignored – never commit real credentials
"""

# ── MQTT (TeslaMate / Mosquitto) ─────────────────────────────────────────── #
MQTT_BROKER = "localhost"       # Mosquitto broker hostname or IP
MQTT_PORT = 1883                # Mosquitto broker TCP port

# ── TeslaMate ────────────────────────────────────────────────────────────── #
TESLAMATE_URL = "http://localhost:4000"   # TeslaMate web UI URL

CAR_ID = 1                      # TeslaMate vehicle ID (default 1)
                                 # Find it in TeslaMate's MQTT topics if you
                                 # have multiple vehicles.
MQTT_NAMESPACE = "teslamate"    # Must match MQTT_NAMESPACE in docker-compose.yml

# ── Tesla Fleet API (for the Control module) ─────────────────────────────── #
TESLA_EMAIL = "your-email@example.com"
# The OAuth token is cached automatically in private/cache.json after the
# first successful login via script/get_token.py.

# ── Logging ──────────────────────────────────────────────────────────────── #
LOG_LEVEL = "INFO"              # DEBUG | INFO | WARNING | ERROR
