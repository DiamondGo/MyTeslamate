"""
Scheduler data models: Condition, Action, Rule.

These are the building blocks of the automation rule system.  Rules are
normally loaded from ``rules.yaml`` via :class:`~tesla.scheduler.loader.RuleLoader`,
but can also be constructed programmatically.

Example::

    rule = Rule(
        name="high_temp_cooling",
        description="Start AC when cabin is too hot and car is plugged in",
        conditions=[
            Condition(field="plugged_in",    operator="eq",  value=True),
            Condition(field="inside_temp",   operator="gt",  value=40.0),
            Condition(field="is_climate_on", operator="eq",  value=False),
        ],
        actions=[
            Action(command="start_climate"),
            Action(command="set_temperature", params={"driver_temp": 22.0}),
        ],
        cooldown_seconds=600,
        trigger_on=["INSIDE_TEMP", "PLUGGED_IN"],
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Supported comparison operators for Condition.
SUPPORTED_OPERATORS = frozenset({
    "eq",       # ==
    "ne",       # !=
    "gt",       # >
    "gte",      # >=
    "lt",       # <
    "lte",      # <=
    "in",       # value in collection
    "not_in",   # value not in collection
    "is_none",  # value is None
    "not_none", # value is not None
})


@dataclass
class Condition:
    """
    A single predicate evaluated against a :class:`~tesla.models.state.TeslaState` field.

    Attributes
    ----------
    field:
        Name of the :class:`~tesla.models.state.TeslaState` attribute to test,
        e.g. ``"inside_temp"``, ``"plugged_in"``, ``"geofence"``.
    operator:
        Comparison operator string.  One of:
        ``"eq"``, ``"ne"``, ``"gt"``, ``"gte"``, ``"lt"``, ``"lte"``,
        ``"in"``, ``"not_in"``, ``"is_none"``, ``"not_none"``.
    value:
        The target value to compare against.  Not used for ``"is_none"``
        and ``"not_none"`` operators.
    """

    field: str
    operator: str
    value: Any = None

    def __post_init__(self) -> None:
        if self.operator not in SUPPORTED_OPERATORS:
            raise ValueError(
                f"Unsupported operator {self.operator!r}. "
                f"Must be one of: {sorted(SUPPORTED_OPERATORS)}"
            )

    def evaluate(self, actual: Any) -> bool:
        """
        Evaluate this condition against *actual* (the current field value).

        Parameters
        ----------
        actual:
            The current value of :attr:`field` from :class:`~tesla.models.state.TeslaState`.

        Returns
        -------
        bool
            ``True`` when the condition is satisfied.
        """
        op = self.operator
        target = self.value

        if op == "is_none":
            return actual is None
        if op == "not_none":
            return actual is not None
        if op == "eq":
            return actual == target
        if op == "ne":
            return actual != target
        if op == "in":
            return actual in target
        if op == "not_in":
            return actual not in target

        # Numeric comparisons – guard against None.
        if actual is None:
            return False
        if op == "gt":
            return actual > target
        if op == "gte":
            return actual >= target
        if op == "lt":
            return actual < target
        if op == "lte":
            return actual <= target

        return False  # unreachable, but satisfies type checkers

    def __repr__(self) -> str:
        return f"Condition({self.field} {self.operator} {self.value!r})"


@dataclass
class Action:
    """
    A command to execute on the :class:`~tesla.controller.TeslaController`.

    Attributes
    ----------
    command:
        Name of the :class:`~tesla.controller.TeslaController` method to call,
        e.g. ``"start_climate"``, ``"set_temperature"``, ``"set_accessory_power"``.
    params:
        Keyword arguments forwarded to the controller method.
    """

    command: str
    params: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        if self.params:
            return f"Action({self.command}({self.params}))"
        return f"Action({self.command}())"


@dataclass
class Rule:
    """
    A complete automation rule: conditions + actions + metadata.

    All :attr:`conditions` must be satisfied simultaneously (AND logic) for
    the rule to fire.  When fired, all :attr:`actions` are executed in order.

    Attributes
    ----------
    name:
        Unique identifier for the rule (used in logs and cooldown tracking).
    description:
        Human-readable description of what the rule does.
    conditions:
        List of :class:`Condition` objects.  ALL must be ``True`` for the
        rule to trigger.
    actions:
        List of :class:`Action` objects executed in order when the rule fires.
    enabled:
        When ``False`` the rule is never evaluated.  Defaults to ``True``.
    cooldown_seconds:
        Minimum number of seconds between consecutive executions of this rule.
        Defaults to ``300`` (5 minutes).
    trigger_on:
        Optional list of :class:`~tesla.models.event.EventType` name strings
        (e.g. ``["INSIDE_TEMP", "PLUGGED_IN"]``).  When provided, the rule is
        only evaluated when one of these event types arrives.  ``None`` means
        evaluate on every event.
    """

    name: str
    description: str = ""
    conditions: List[Condition] = field(default_factory=list)
    actions: List[Action] = field(default_factory=list)
    enabled: bool = True
    cooldown_seconds: int = 300
    trigger_on: Optional[List[str]] = None

    def is_triggered_by(self, event_type_name: str) -> bool:
        """Return ``True`` if this rule should be evaluated for the given event type name.

        Parameters
        ----------
        event_type_name:
            The :class:`~tesla.models.event.EventType` name string,
            e.g. ``"INSIDE_TEMP"``.
        """
        if self.trigger_on is None:
            return True  # evaluate on every event
        return event_type_name in self.trigger_on

    def __repr__(self) -> str:
        status = "enabled" if self.enabled else "disabled"
        return (
            f"Rule({self.name!r}, {len(self.conditions)} conditions, "
            f"{len(self.actions)} actions, cooldown={self.cooldown_seconds}s, {status})"
        )
