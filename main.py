#!/usr/bin/env python3
"""
Tesla Automation System – CLI entry point.

Reads configuration from ``config.py`` and rules from ``rules.yaml``
(or the paths specified via command-line arguments), then starts the
automation loop.

Usage::

    # Normal mode (executes real API commands)
    python main.py

    # Dry-run mode (evaluates rules but does NOT call Tesla API)
    python main.py --dry-run

    # Custom rules file
    python main.py --rules /path/to/my-rules.yaml

    # Verbose logging
    python main.py --log-level DEBUG
"""

from __future__ import annotations

import argparse
import logging
import sys


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Tesla Automation System – monitor, schedule, and control your Tesla.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--rules",
        default="rules.yaml",
        metavar="PATH",
        help="Path to the YAML rules file (default: rules.yaml)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Evaluate rules but do NOT send any commands to the vehicle.",
    )
    parser.add_argument(
        "--log-level",
        default=None,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        metavar="LEVEL",
        help="Override the log level from config.py (DEBUG/INFO/WARNING/ERROR).",
    )
    return parser.parse_args()


def _setup_logging(level_str: str) -> None:
    level = getattr(logging, level_str.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main() -> None:
    args = _parse_args()

    # ── Load config ──────────────────────────────────────────────────── #
    try:
        import config  # type: ignore[import]
    except ImportError:
        print(
            "ERROR: config.py not found.\n"
            "Copy config.example.py to config.py and fill in your settings.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Determine log level: CLI arg > config.py > default INFO.
    log_level = args.log_level or getattr(config, "LOG_LEVEL", "INFO")
    _setup_logging(log_level)

    logger = logging.getLogger(__name__)

    # ── Validate required config keys ────────────────────────────────── #
    required_keys = ["MQTT_BROKER", "MQTT_PORT", "CAR_ID", "MQTT_NAMESPACE", "TESLA_EMAIL"]
    missing = [k for k in required_keys if not hasattr(config, k)]
    if missing:
        logger.error(
            "config.py is missing required key(s): %s\n"
            "See config.example.py for reference.",
            ", ".join(missing),
        )
        sys.exit(1)

    # ── Check rules file exists ──────────────────────────────────────── #
    import os
    if not os.path.isfile(args.rules):
        logger.error(
            "Rules file not found: %s\n"
            "Copy rules.example.yaml to rules.yaml and customise it.",
            args.rules,
        )
        sys.exit(1)

    # ── Start the automation app ─────────────────────────────────────── #
    from tesla.app import AutomationApp

    app = AutomationApp(
        mqtt_broker=config.MQTT_BROKER,
        mqtt_port=config.MQTT_PORT,
        car_id=config.CAR_ID,
        mqtt_namespace=config.MQTT_NAMESPACE,
        tesla_email=config.TESLA_EMAIL,
        rules_path=args.rules,
        dry_run=args.dry_run,
    )

    app.run()


if __name__ == "__main__":
    main()
