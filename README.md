# Tesla Automation System

An event-driven automation system for Tesla vehicles built on top of [TeslaMate](https://github.com/teslamate-org/teslamate).

It monitors your vehicle via MQTT, evaluates user-defined rules, and controls the vehicle via the Tesla Fleet API.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Tesla Automation System                      │
│                                                                  │
│  ┌──────────────┐    ┌──────────────────┐    ┌───────────────┐  │
│  │   Monitor    │───▶│    Scheduler     │───▶│   Controller  │  │
│  │              │    │                  │    │               │  │
│  │ TeslaMQTT    │    │ RuleEngine       │    │ TeslaControl  │  │
│  │ Client       │    │ + CooldownMgr    │    │ ler (teslapy) │  │
│  │              │    │ + YAML Rules     │    │               │  │
│  └──────────────┘    └──────────────────┘    └───────────────┘  │
│         ▲                                            │           │
│         │                                            ▼           │
│   Mosquitto MQTT                           Tesla Fleet API       │
│   (TeslaMate)                              (via teslapy)         │
└─────────────────────────────────────────────────────────────────┘
```

### Modules

| Module | Package | Description |
|--------|---------|-------------|
| **Monitor** | `tesla/` | Subscribes to TeslaMate MQTT, maintains live `TeslaState`, emits `TeslaEvent` callbacks |
| **Scheduler** | `tesla/scheduler/` | Evaluates YAML-defined rules against state, enforces cooldowns, dispatches actions |
| **Controller** | `tesla/controller.py` | Sends commands to the vehicle via Tesla Fleet API using `teslapy` |

---

## Prerequisites

- [TeslaMate](https://github.com/teslamate-org/teslamate) running with Mosquitto MQTT broker
- Python 3.12+
- Tesla account credentials (for Fleet API control)

---

## Installation

```bash
# 1. Clone / enter the project directory
cd /path/to/teslamate-automation

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure
cp config.example.py config.py
# Edit config.py with your MQTT broker address, car ID, and Tesla email

# 5. Authenticate with Tesla Fleet API (one-time)
python script/get_token.py
# Follow the browser prompts – token is cached in private/cache.json

# 6. Set up your automation rules
cp rules.example.yaml rules.yaml
# Edit rules.yaml to enable/customise the rules you want
```

---

## Configuration

Edit `config.py` (copied from `config.example.py`):

```python
# MQTT broker (Mosquitto, usually on the same host as TeslaMate)
MQTT_BROKER = "localhost"
MQTT_PORT   = 1883

# TeslaMate settings
CAR_ID         = 1              # Vehicle ID in TeslaMate
MQTT_NAMESPACE = "teslamate"    # Matches MQTT_NAMESPACE in docker-compose.yml

# Tesla account (for Fleet API commands)
TESLA_EMAIL = "you@example.com"

# Logging
LOG_LEVEL = "INFO"   # DEBUG | INFO | WARNING | ERROR
```

---

## Running

```bash
# Normal mode – evaluates rules and sends real commands to the vehicle
python main.py

# Dry-run mode – evaluates rules but does NOT send any API commands
python main.py --dry-run

# Custom rules file
python main.py --rules /path/to/my-rules.yaml

# Verbose logging
python main.py --log-level DEBUG

# Help
python main.py --help
```

---

## Automation Rules

Rules are defined in `rules.yaml` (copied from `rules.example.yaml`).

### Rule structure

```yaml
rules:
  - name: "unique_rule_name"          # Required. Used in logs and cooldown tracking.
    description: "What this rule does" # Optional.
    enabled: true                      # Set to false to disable without deleting.
    cooldown_seconds: 300              # Min seconds between executions (default 300).
    trigger_on:                        # Only evaluate when these MQTT events arrive.
      - INSIDE_TEMP                    # EventType names (see tesla/models/event.py).
      - PLUGGED_IN
    conditions:                        # ALL must be true for the rule to fire (AND logic).
      - field: inside_temp             # TeslaState field name.
        operator: gt                   # Comparison operator.
        value: 40.0                    # Target value.
    actions:                           # Executed in order when all conditions are met.
      - command: start_climate         # TeslaController method name.
      - command: set_temperature
        params:
          driver_temp: 22.0
```

### Built-in use cases (in `rules.example.yaml`)

#### 1. High cabin temperature cooling

When the car is **plugged in** and the **cabin temperature exceeds 40 °C**, automatically start the HVAC and set it to 22 °C.

```yaml
- name: "high_temp_cooling"
  conditions:
    - field: plugged_in
      operator: eq
      value: true
    - field: inside_temp
      operator: gt
      value: 40.0
    - field: is_climate_on
      operator: eq
      value: false
  actions:
    - command: start_climate
    - command: set_temperature
      params:
        driver_temp: 22.0
```

#### 2. Home charging – enable accessory power

When the car is **plugged in at Home** (TeslaMate geofence), enable "Keep Accessory Power On" so 12V accessories (dashcam, etc.) stay powered during charging.

```yaml
- name: "home_charging_accessory_power"
  conditions:
    - field: plugged_in
      operator: eq
      value: true
    - field: geofence
      operator: eq
      value: "Home"
    - field: keep_accessory_power_on
      operator: eq
      value: false
  actions:
    - command: set_accessory_power
      params:
        on: true
```

### Supported operators

| Operator | Meaning |
|----------|---------|
| `eq` | `field == value` |
| `ne` | `field != value` |
| `gt` | `field > value` (numeric) |
| `gte` | `field >= value` (numeric) |
| `lt` | `field < value` (numeric) |
| `lte` | `field <= value` (numeric) |
| `in` | `field in [list]` |
| `not_in` | `field not in [list]` |
| `is_none` | `field is None` |
| `not_none` | `field is not None` |

### Supported commands

| Command | Parameters | Description |
|---------|-----------|-------------|
| `start_climate` | — | Turn on HVAC |
| `stop_climate` | — | Turn off HVAC |
| `set_temperature` | `driver_temp`, `passenger_temp` (opt) | Set temperature setpoint (°C) |
| `start_climate_keeper` | `mode` (`on`/`dog`/`camp`) | Enable Climate Keeper |
| `start_charging` | — | Start charging |
| `stop_charging` | — | Stop charging |
| `set_charge_limit` | `percent` | Set charge limit (0–100) |
| `open_charge_port` | — | Open charge port door |
| `close_charge_port` | — | Close charge port door |
| `lock` | — | Lock doors |
| `unlock` | — | Unlock doors |
| `enable_sentry_mode` | — | Enable Sentry Mode |
| `disable_sentry_mode` | — | Disable Sentry Mode |
| `vent_windows` | — | Vent all windows |
| `close_windows` | — | Close all windows |
| `set_accessory_power` | `on` (bool) | Enable/disable accessory power |
| `wake_up` | — | Wake vehicle from sleep |
| `execute_command` | `command`, + extras | Send arbitrary teslapy command |

---

## Running as a System Service

```bash
# Copy and edit the service file
sudo cp tesla-charging-manager.service /etc/systemd/system/tesla-automation.service
# Edit the service file to point to main.py

sudo systemctl daemon-reload
sudo systemctl enable tesla-automation
sudo systemctl start tesla-automation

# View logs
sudo journalctl -u tesla-automation -f
```

---

## Development

### Running tests

```bash
# Activate virtual environment
source venv/bin/activate

# Run all tests
pytest tests/ -v

# Run a specific test file
pytest tests/test_engine.py -v

# Run with coverage
pytest tests/ --cov=tesla --cov-report=html
```

### Project structure

```
teslamate/
├── config.example.py          # Configuration template
├── config.py                  # Your local config (gitignored)
├── rules.example.yaml         # Example rules with documentation
├── rules.yaml                 # Your active rules (gitignored)
├── main.py                    # CLI entry point
├── requirements.txt
├── docker-compose.yml         # TeslaMate + Mosquitto + Grafana
├── tesla/
│   ├── __init__.py
│   ├── mqtt_client.py         # Monitor: TeslaMQTTClient
│   ├── controller.py          # Control: TeslaController (Fleet API)
│   ├── app.py                 # AutomationApp (wires all modules)
│   ├── models/
│   │   ├── state.py           # TeslaState dataclass (60+ fields)
│   │   └── event.py           # TeslaEvent + EventType enum
│   └── scheduler/
│       ├── models.py          # Condition, Action, Rule dataclasses
│       ├── cooldown.py        # CooldownManager
│       ├── loader.py          # YAML rule loader + validation
│       └── engine.py          # RuleEngine
├── tests/
│   ├── test_condition.py
│   ├── test_cooldown.py
│   ├── test_engine.py
│   └── test_loader.py
├── script/                    # Utility scripts
│   ├── get_token.py           # Tesla OAuth token helper
│   ├── get_mqtt_status.py     # Quick MQTT state snapshot
│   ├── monitor_live.py        # Live MQTT message viewer
│   └── monitor_temp.py        # Temperature monitoring demo
└── private/                   # Gitignored – store cache.json here
```

### Monitoring scripts (standalone)

| Script | Description |
|--------|-------------|
| `script/get_mqtt_status.py` | Snapshot of current vehicle state from MQTT |
| `script/monitor_live.py` | Live MQTT message viewer with emoji annotations |
| `script/monitor_temp.py` | Temperature monitoring demo (3 usage patterns) |
| `script/get_token.py` | Tesla OAuth token helper (run once) |

---

## TeslaMate MQTT Topics

TeslaMate publishes vehicle state to:
```
teslamate/<MQTT_NAMESPACE>/cars/<CAR_ID>/<topic>
```

Key topics used by this system:

| Topic | Type | Description |
|-------|------|-------------|
| `plugged_in` | bool | Charge cable connected |
| `charging_state` | str | Charging / Complete / Disconnected / Stopped |
| `battery_level` | int | State of charge (%) |
| `inside_temp` | float | Cabin temperature (°C) |
| `outside_temp` | float | Ambient temperature (°C) |
| `is_climate_on` | bool | HVAC active |
| `geofence` | str | TeslaMate geofence name (e.g. "Home") |
| `state` | str | online / asleep / offline / charging |
| `keep_accessory_power_on` | bool | Accessory power state |
| `latitude` / `longitude` | float | GPS coordinates |
| `locked` | bool | Door lock state |
| `sentry_mode` | bool | Sentry Mode active |

---

## License

MIT License
