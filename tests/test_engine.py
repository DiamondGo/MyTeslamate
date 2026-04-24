"""
Unit tests for tesla.scheduler.engine.RuleEngine.

Uses a mock TeslaController so no real API calls are made.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from tesla.models.event import EventType, TeslaEvent
from tesla.models.state import TeslaState
from tesla.scheduler.cooldown import CooldownManager
from tesla.scheduler.engine import RuleEngine
from tesla.scheduler.models import Action, Condition, Rule


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_state(**kwargs) -> TeslaState:
    """Return a TeslaState with the given fields set."""
    return TeslaState(**kwargs)


def _make_event(event_type: EventType, state: TeslaState, new_value=None) -> TeslaEvent:
    """Return a minimal TeslaEvent for testing."""
    return TeslaEvent(
        event_type=event_type,
        topic_key=event_type.value,
        old_value=None,
        new_value=new_value,
        raw_payload=str(new_value),
        timestamp=datetime.now(),
        state=state,
        is_initial=False,
    )


def _make_rule(
    name: str = "test_rule",
    conditions=None,
    actions=None,
    cooldown_seconds: int = 0,
    trigger_on=None,
    enabled: bool = True,
) -> Rule:
    return Rule(
        name=name,
        description="Test rule",
        conditions=conditions or [],
        actions=actions or [Action(command="start_climate")],
        enabled=enabled,
        cooldown_seconds=cooldown_seconds,
        trigger_on=trigger_on,
    )


def _make_controller(**method_returns) -> MagicMock:
    """Return a mock TeslaController where each method returns the given value."""
    ctrl = MagicMock()
    for method, return_value in method_returns.items():
        getattr(ctrl, method).return_value = return_value
    # Default: all methods return True (success)
    ctrl.start_climate.return_value = True
    ctrl.stop_climate.return_value = True
    ctrl.set_temperature.return_value = True
    ctrl.set_accessory_power.return_value = True
    return ctrl


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestRuleEngineEvaluate:
    """Tests for RuleEngine.evaluate()."""

    def test_rule_fires_when_conditions_met(self):
        state = _make_state(inside_temp=42.0, plugged_in=True, is_climate_on=False)
        rule = _make_rule(
            conditions=[
                Condition("plugged_in", "eq", True),
                Condition("inside_temp", "gt", 40.0),
                Condition("is_climate_on", "eq", False),
            ],
            actions=[Action("start_climate")],
            cooldown_seconds=0,
        )
        ctrl = _make_controller()
        engine = RuleEngine(controller=ctrl, rules=[rule])
        event = _make_event(EventType.INSIDE_TEMP, state, new_value=42.0)

        triggered = engine.evaluate(event)

        assert "test_rule" in triggered
        ctrl.start_climate.assert_called_once()

    def test_rule_does_not_fire_when_condition_fails(self):
        state = _make_state(inside_temp=35.0, plugged_in=True, is_climate_on=False)
        rule = _make_rule(
            conditions=[
                Condition("inside_temp", "gt", 40.0),
            ],
            cooldown_seconds=0,
        )
        ctrl = _make_controller()
        engine = RuleEngine(controller=ctrl, rules=[rule])
        event = _make_event(EventType.INSIDE_TEMP, state, new_value=35.0)

        triggered = engine.evaluate(event)

        assert triggered == []
        ctrl.start_climate.assert_not_called()

    def test_disabled_rule_is_skipped(self):
        state = _make_state(inside_temp=45.0)
        rule = _make_rule(
            conditions=[Condition("inside_temp", "gt", 40.0)],
            enabled=False,
            cooldown_seconds=0,
        )
        ctrl = _make_controller()
        engine = RuleEngine(controller=ctrl, rules=[rule])
        event = _make_event(EventType.INSIDE_TEMP, state, new_value=45.0)

        triggered = engine.evaluate(event)

        assert triggered == []
        ctrl.start_climate.assert_not_called()

    def test_trigger_on_filters_events(self):
        """Rule with trigger_on=["PLUGGED_IN"] should not fire on INSIDE_TEMP events."""
        state = _make_state(plugged_in=True)
        rule = _make_rule(
            conditions=[Condition("plugged_in", "eq", True)],
            trigger_on=["PLUGGED_IN"],
            cooldown_seconds=0,
        )
        ctrl = _make_controller()
        engine = RuleEngine(controller=ctrl, rules=[rule])

        # Wrong event type – should be filtered out.
        event = _make_event(EventType.INSIDE_TEMP, state, new_value=42.0)
        triggered = engine.evaluate(event)
        assert triggered == []
        ctrl.start_climate.assert_not_called()

        # Correct event type – should fire.
        event2 = _make_event(EventType.PLUGGED_IN, state, new_value=True)
        triggered2 = engine.evaluate(event2)
        assert "test_rule" in triggered2
        ctrl.start_climate.assert_called_once()

    def test_cooldown_prevents_repeated_execution(self):
        state = _make_state(inside_temp=45.0)
        rule = _make_rule(
            conditions=[Condition("inside_temp", "gt", 40.0)],
            cooldown_seconds=300,
        )
        ctrl = _make_controller()
        # Use a fixed-time cooldown manager.
        time_val = [0.0]
        cooldown = CooldownManager(clock=lambda: time_val[0])
        engine = RuleEngine(controller=ctrl, rules=[rule], cooldown=cooldown)
        event = _make_event(EventType.INSIDE_TEMP, state, new_value=45.0)

        # First evaluation – should fire.
        triggered1 = engine.evaluate(event)
        assert "test_rule" in triggered1
        assert ctrl.start_climate.call_count == 1

        # Second evaluation immediately – should be blocked by cooldown.
        triggered2 = engine.evaluate(event)
        assert triggered2 == []
        assert ctrl.start_climate.call_count == 1  # still 1

        # Advance time past cooldown.
        time_val[0] = 301.0
        triggered3 = engine.evaluate(event)
        assert "test_rule" in triggered3
        assert ctrl.start_climate.call_count == 2

    def test_multiple_actions_executed_in_order(self):
        state = _make_state(plugged_in=True, inside_temp=45.0, is_climate_on=False)
        call_order = []

        ctrl = MagicMock()
        ctrl.start_climate.side_effect = lambda: call_order.append("start_climate") or True
        ctrl.set_temperature.side_effect = lambda **kw: call_order.append("set_temperature") or True

        rule = _make_rule(
            conditions=[Condition("inside_temp", "gt", 40.0)],
            actions=[
                Action("start_climate"),
                Action("set_temperature", params={"driver_temp": 22.0}),
            ],
            cooldown_seconds=0,
        )
        engine = RuleEngine(controller=ctrl, rules=[rule])
        event = _make_event(EventType.INSIDE_TEMP, state, new_value=45.0)

        engine.evaluate(event)

        assert call_order == ["start_climate", "set_temperature"]
        ctrl.set_temperature.assert_called_once_with(driver_temp=22.0)

    def test_dry_run_does_not_call_controller(self):
        state = _make_state(inside_temp=45.0)
        rule = _make_rule(
            conditions=[Condition("inside_temp", "gt", 40.0)],
            cooldown_seconds=0,
        )
        ctrl = _make_controller()
        engine = RuleEngine(controller=ctrl, rules=[rule], dry_run=True)
        event = _make_event(EventType.INSIDE_TEMP, state, new_value=45.0)

        triggered = engine.evaluate(event)

        # In dry-run mode, the rule is considered "triggered" (conditions met)
        # but no controller methods are called.
        assert "test_rule" in triggered
        ctrl.start_climate.assert_not_called()

    def test_failed_action_does_not_start_cooldown(self):
        state = _make_state(inside_temp=45.0)
        rule = _make_rule(
            conditions=[Condition("inside_temp", "gt", 40.0)],
            cooldown_seconds=300,
        )
        ctrl = _make_controller()
        ctrl.start_climate.return_value = False  # simulate failure

        time_val = [0.0]
        cooldown = CooldownManager(clock=lambda: time_val[0])
        engine = RuleEngine(controller=ctrl, rules=[rule], cooldown=cooldown)
        event = _make_event(EventType.INSIDE_TEMP, state, new_value=45.0)

        # First call – action fails, cooldown should NOT be recorded.
        triggered = engine.evaluate(event)
        assert triggered == []  # not in triggered because action failed

        # Second call immediately – should try again (no cooldown was set).
        ctrl.start_climate.return_value = True
        triggered2 = engine.evaluate(event)
        assert "test_rule" in triggered2

    def test_unknown_command_returns_false(self):
        state = _make_state(inside_temp=45.0)
        rule = _make_rule(
            conditions=[Condition("inside_temp", "gt", 40.0)],
            actions=[Action("nonexistent_command")],
            cooldown_seconds=0,
        )
        ctrl = MagicMock(spec=[])  # no attributes
        engine = RuleEngine(controller=ctrl, rules=[rule])
        event = _make_event(EventType.INSIDE_TEMP, state, new_value=45.0)

        triggered = engine.evaluate(event)
        assert triggered == []  # action failed → not triggered

    def test_no_conditions_always_fires(self):
        """A rule with no conditions should fire on every matching event."""
        state = _make_state()
        rule = _make_rule(conditions=[], cooldown_seconds=0)
        ctrl = _make_controller()
        engine = RuleEngine(controller=ctrl, rules=[rule])
        event = _make_event(EventType.STATE, state, new_value="online")

        triggered = engine.evaluate(event)
        assert "test_rule" in triggered


class TestRuleEngineManagement:
    """Tests for add_rule / remove_rule / get_rule."""

    def test_add_rule(self):
        ctrl = _make_controller()
        engine = RuleEngine(controller=ctrl, rules=[])
        rule = _make_rule(name="new_rule")
        engine.add_rule(rule)
        assert engine.get_rule("new_rule") is rule

    def test_remove_rule(self):
        ctrl = _make_controller()
        rule = _make_rule(name="to_remove")
        engine = RuleEngine(controller=ctrl, rules=[rule])
        removed = engine.remove_rule("to_remove")
        assert removed is True
        assert engine.get_rule("to_remove") is None

    def test_remove_nonexistent_rule(self):
        ctrl = _make_controller()
        engine = RuleEngine(controller=ctrl, rules=[])
        removed = engine.remove_rule("ghost")
        assert removed is False

    def test_get_rule_not_found(self):
        ctrl = _make_controller()
        engine = RuleEngine(controller=ctrl, rules=[])
        assert engine.get_rule("missing") is None

    def test_repr(self):
        ctrl = _make_controller()
        rule = _make_rule()
        engine = RuleEngine(controller=ctrl, rules=[rule])
        r = repr(engine)
        assert "1 rules" in r
        assert "1 enabled" in r

    def test_repr_dry_run(self):
        ctrl = _make_controller()
        engine = RuleEngine(controller=ctrl, rules=[], dry_run=True)
        assert "DRY-RUN" in repr(engine)
