"""
RuleLoader – loads and validates Rule objects from a YAML file.

The YAML format is documented in ``rules.example.yaml``.

Usage::

    loader = RuleLoader(state_fields=TeslaState.__dataclass_fields__)
    rules = loader.load("rules.yaml")

Validation performed at load time:
  - Required keys present (``name``, ``conditions``, ``actions``)
  - ``conditions[].field`` exists on TeslaState
  - ``conditions[].operator`` is a supported operator
  - ``actions[].command`` is a valid TeslaController method name
  - ``trigger_on`` event names are valid EventType names
"""

from __future__ import annotations

import logging
from dataclasses import fields as dataclass_fields
from typing import Any, Dict, List, Optional, Set

import yaml

from tesla.models.event import EventType
from tesla.models.state import TeslaState
from tesla.scheduler.models import Action, Condition, Rule, SUPPORTED_OPERATORS

logger = logging.getLogger(__name__)

# Valid TeslaController public method names (commands that can be used in actions).
VALID_COMMANDS: Set[str] = {
    "start_climate",
    "stop_climate",
    "set_temperature",
    "start_climate_keeper",
    "start_charging",
    "stop_charging",
    "set_charge_limit",
    "open_charge_port",
    "close_charge_port",
    "lock",
    "unlock",
    "enable_sentry_mode",
    "disable_sentry_mode",
    "vent_windows",
    "close_windows",
    "set_accessory_power",
    "wake_up",
    "execute_command",
}

# Valid TeslaState field names (computed once at import time).
_STATE_FIELDS: Set[str] = {f.name for f in dataclass_fields(TeslaState)} - {"updated_at"}

# Valid EventType names.
_EVENT_TYPE_NAMES: Set[str] = {e.name for e in EventType}


class RuleValidationError(ValueError):
    """Raised when a rule definition in the YAML file is invalid."""


class RuleLoader:
    """
    Loads :class:`~tesla.scheduler.models.Rule` objects from a YAML file.

    Parameters
    ----------
    strict:
        When ``True`` (default), raise :class:`RuleValidationError` on the
        first invalid rule.  When ``False``, log a warning and skip invalid
        rules instead.
    """

    def __init__(self, strict: bool = True) -> None:
        self.strict = strict

    def load(self, yaml_path: str) -> List[Rule]:
        """
        Parse *yaml_path* and return a list of validated :class:`~tesla.scheduler.models.Rule` objects.

        Parameters
        ----------
        yaml_path:
            Path to the YAML rules file.

        Returns
        -------
        List[Rule]
            Validated rules.  Disabled rules are included (the engine skips them).

        Raises
        ------
        FileNotFoundError
            If *yaml_path* does not exist.
        yaml.YAMLError
            If the file is not valid YAML.
        RuleValidationError
            If ``strict=True`` and any rule definition is invalid.
        """
        logger.info("Loading rules from %s …", yaml_path)

        with open(yaml_path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)

        if not isinstance(data, dict) or "rules" not in data:
            raise RuleValidationError(
                f"{yaml_path}: top-level key 'rules' is missing or file is empty."
            )

        raw_rules: List[Dict[str, Any]] = data["rules"]
        if not isinstance(raw_rules, list):
            raise RuleValidationError(f"{yaml_path}: 'rules' must be a list.")

        rules: List[Rule] = []
        for i, raw in enumerate(raw_rules):
            try:
                rule = self._parse_rule(raw, index=i)
                rules.append(rule)
            except RuleValidationError as exc:
                if self.strict:
                    raise
                logger.warning("Skipping invalid rule at index %d: %s", i, exc)

        enabled = sum(1 for r in rules if r.enabled)
        logger.info(
            "Loaded %d rule(s) from %s (%d enabled).",
            len(rules), yaml_path, enabled,
        )
        return rules

    # ------------------------------------------------------------------ #
    # Internal parsing helpers
    # ------------------------------------------------------------------ #

    def _parse_rule(self, raw: Dict[str, Any], index: int) -> Rule:
        """Parse and validate a single raw rule dict."""
        if not isinstance(raw, dict):
            raise RuleValidationError(f"Rule at index {index} must be a mapping, got {type(raw).__name__}.")

        name = raw.get("name")
        if not name or not isinstance(name, str):
            raise RuleValidationError(f"Rule at index {index}: 'name' is required and must be a non-empty string.")

        description = raw.get("description", "")
        enabled = bool(raw.get("enabled", True))
        cooldown_seconds = int(raw.get("cooldown_seconds", 300))

        # Parse trigger_on.
        trigger_on: Optional[List[str]] = None
        raw_trigger = raw.get("trigger_on")
        if raw_trigger is not None:
            if not isinstance(raw_trigger, list):
                raise RuleValidationError(f"Rule {name!r}: 'trigger_on' must be a list of EventType names.")
            trigger_on = []
            for et_name in raw_trigger:
                if et_name not in _EVENT_TYPE_NAMES:
                    raise RuleValidationError(
                        f"Rule {name!r}: unknown EventType {et_name!r} in 'trigger_on'. "
                        f"Valid names: {sorted(_EVENT_TYPE_NAMES)}"
                    )
                trigger_on.append(et_name)

        # Parse conditions.
        raw_conditions = raw.get("conditions", [])
        if not isinstance(raw_conditions, list):
            raise RuleValidationError(f"Rule {name!r}: 'conditions' must be a list.")
        conditions = [self._parse_condition(c, rule_name=name) for c in raw_conditions]

        # Parse actions.
        raw_actions = raw.get("actions", [])
        if not isinstance(raw_actions, list):
            raise RuleValidationError(f"Rule {name!r}: 'actions' must be a list.")
        if not raw_actions:
            raise RuleValidationError(f"Rule {name!r}: 'actions' must not be empty.")
        actions = [self._parse_action(a, rule_name=name) for a in raw_actions]

        return Rule(
            name=name,
            description=description,
            conditions=conditions,
            actions=actions,
            enabled=enabled,
            cooldown_seconds=cooldown_seconds,
            trigger_on=trigger_on,
        )

    def _parse_condition(self, raw: Dict[str, Any], rule_name: str) -> Condition:
        """Parse and validate a single condition dict."""
        if not isinstance(raw, dict):
            raise RuleValidationError(
                f"Rule {rule_name!r}: each condition must be a mapping, got {type(raw).__name__}."
            )

        field_name = raw.get("field")
        if not field_name or not isinstance(field_name, str):
            raise RuleValidationError(
                f"Rule {rule_name!r}: condition 'field' is required and must be a string."
            )
        if field_name not in _STATE_FIELDS:
            raise RuleValidationError(
                f"Rule {rule_name!r}: condition field {field_name!r} does not exist on TeslaState. "
                f"Valid fields: {sorted(_STATE_FIELDS)}"
            )

        operator = raw.get("operator")
        if not operator or not isinstance(operator, str):
            raise RuleValidationError(
                f"Rule {rule_name!r}: condition 'operator' is required and must be a string."
            )
        if operator not in SUPPORTED_OPERATORS:
            raise RuleValidationError(
                f"Rule {rule_name!r}: unsupported operator {operator!r}. "
                f"Supported: {sorted(SUPPORTED_OPERATORS)}"
            )

        value = raw.get("value")  # None is valid for is_none / not_none operators

        return Condition(field=field_name, operator=operator, value=value)

    def _parse_action(self, raw: Dict[str, Any], rule_name: str) -> Action:
        """Parse and validate a single action dict."""
        if not isinstance(raw, dict):
            raise RuleValidationError(
                f"Rule {rule_name!r}: each action must be a mapping, got {type(raw).__name__}."
            )

        command = raw.get("command")
        if not command or not isinstance(command, str):
            raise RuleValidationError(
                f"Rule {rule_name!r}: action 'command' is required and must be a string."
            )
        if command not in VALID_COMMANDS:
            raise RuleValidationError(
                f"Rule {rule_name!r}: unknown command {command!r}. "
                f"Valid commands: {sorted(VALID_COMMANDS)}"
            )

        params = raw.get("params", {})
        if not isinstance(params, dict):
            raise RuleValidationError(
                f"Rule {rule_name!r}: action 'params' must be a mapping, got {type(params).__name__}."
            )

        return Action(command=command, params=params)
