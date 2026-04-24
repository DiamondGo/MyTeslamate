"""
RuleEngine – evaluates rules against TeslaState and dispatches actions.

The engine is wired into :class:`~tesla.mqtt_client.TeslaMQTTClient` via
``client.on_any(engine.evaluate)``.  On every incoming MQTT event it:

  1. Filters rules by ``trigger_on`` (if specified on the rule).
  2. Evaluates all conditions against the current :class:`~tesla.models.state.TeslaState`.
  3. Checks the per-rule cooldown via :class:`~tesla.scheduler.cooldown.CooldownManager`.
  4. Executes actions via :class:`~tesla.controller.TeslaController`.

Usage::

    from tesla import TeslaMQTTClient, TeslaController
    from tesla.scheduler import RuleEngine, RuleLoader

    rules = RuleLoader().load("rules.yaml")
    engine = RuleEngine(controller=ctrl, rules=rules)

    client = TeslaMQTTClient(...)
    client.on_any(engine.evaluate)
    client.start()

Dry-run mode::

    engine = RuleEngine(controller=ctrl, rules=rules, dry_run=True)
    # Actions are logged but NOT sent to the vehicle.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from tesla.controller import TeslaController
from tesla.models.event import TeslaEvent
from tesla.models.state import TeslaState
from tesla.scheduler.cooldown import CooldownManager
from tesla.scheduler.models import Action, Condition, Rule

logger = logging.getLogger(__name__)


class RuleEngine:
    """
    Evaluates automation rules against the live vehicle state.

    Parameters
    ----------
    controller:
        :class:`~tesla.controller.TeslaController` used to execute actions.
    rules:
        List of :class:`~tesla.scheduler.models.Rule` objects to evaluate.
    cooldown:
        Optional :class:`~tesla.scheduler.cooldown.CooldownManager`.
        A new one is created if not provided.
    dry_run:
        When ``True``, conditions are evaluated and logged but actions are
        **not** sent to the vehicle.  Useful for testing rule logic.
    """

    def __init__(
        self,
        controller: TeslaController,
        rules: Optional[List[Rule]] = None,
        cooldown: Optional[CooldownManager] = None,
        dry_run: bool = False,
    ) -> None:
        self.controller = controller
        self.rules: List[Rule] = rules or []
        self.cooldown = cooldown or CooldownManager()
        self.dry_run = dry_run

        if dry_run:
            logger.warning(
                "RuleEngine is in DRY-RUN mode – actions will be logged but NOT executed."
            )

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def evaluate(self, event: TeslaEvent) -> List[str]:
        """
        Evaluate all enabled rules against the current vehicle state.

        This method is designed to be passed directly as a callback to
        :meth:`~tesla.mqtt_client.TeslaMQTTClient.on_any`.

        Parameters
        ----------
        event:
            The incoming :class:`~tesla.models.event.TeslaEvent`.

        Returns
        -------
        List[str]
            Names of rules that were triggered (conditions met + actions executed).
        """
        triggered: List[str] = []
        state = event.state  # snapshot taken at event time
        event_type_name = event.event_type.name

        for rule in self.rules:
            if not rule.enabled:
                continue

            # Filter by trigger_on.
            if not rule.is_triggered_by(event_type_name):
                logger.debug(
                    "Rule %r: skipped (event %s not in trigger_on).",
                    rule.name, event_type_name,
                )
                continue

            # Evaluate all conditions.
            if not self._all_conditions_met(rule, state):
                continue

            # Check cooldown.
            if not self.cooldown.can_execute(rule.name, rule.cooldown_seconds):
                logger.info(
                    "Rule %r: conditions met but in cooldown – skipping.",
                    rule.name,
                )
                continue

            # Execute actions.
            logger.info(
                "Rule %r triggered by event %s – executing %d action(s).",
                rule.name, event_type_name, len(rule.actions),
            )
            success = self._execute_actions(rule)

            if success:
                self.cooldown.record_execution(rule.name)
                triggered.append(rule.name)
            else:
                logger.warning(
                    "Rule %r: one or more actions failed – cooldown NOT started.",
                    rule.name,
                )

        return triggered

    def add_rule(self, rule: Rule) -> None:
        """Add a rule to the engine at runtime."""
        self.rules.append(rule)
        logger.info("Rule %r added to engine.", rule.name)

    def remove_rule(self, rule_name: str) -> bool:
        """Remove a rule by name.  Returns ``True`` if found and removed."""
        before = len(self.rules)
        self.rules = [r for r in self.rules if r.name != rule_name]
        removed = len(self.rules) < before
        if removed:
            logger.info("Rule %r removed from engine.", rule_name)
        return removed

    def get_rule(self, rule_name: str) -> Optional[Rule]:
        """Return the rule with the given name, or ``None`` if not found."""
        for rule in self.rules:
            if rule.name == rule_name:
                return rule
        return None

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _all_conditions_met(self, rule: Rule, state: TeslaState) -> bool:
        """Return ``True`` when every condition in *rule* is satisfied."""
        for condition in rule.conditions:
            actual = getattr(state, condition.field, None)
            result = condition.evaluate(actual)
            if not result:
                logger.debug(
                    "Rule %r: condition %r not met (actual=%r).",
                    rule.name, condition, actual,
                )
                return False
        logger.debug("Rule %r: all %d condition(s) met.", rule.name, len(rule.conditions))
        return True

    def _execute_actions(self, rule: Rule) -> bool:
        """
        Execute all actions for *rule* in order.

        Returns ``True`` if all actions succeeded, ``False`` if any failed.
        In dry-run mode, actions are logged but not executed (always returns ``True``).
        """
        all_ok = True
        for action in rule.actions:
            if self.dry_run:
                logger.info(
                    "[DRY-RUN] Would execute: %s(%s)",
                    action.command,
                    ", ".join(f"{k}={v!r}" for k, v in action.params.items()),
                )
                continue

            ok = self._dispatch_action(action)
            if not ok:
                logger.error(
                    "Rule %r: action %r failed.", rule.name, action.command
                )
                all_ok = False
                # Continue executing remaining actions even if one fails.

        return all_ok

    def _dispatch_action(self, action: Action) -> bool:
        """Call the appropriate :class:`~tesla.controller.TeslaController` method."""
        method = getattr(self.controller, action.command, None)
        if method is None:
            logger.error(
                "Action command %r not found on TeslaController.", action.command
            )
            return False

        try:
            result = method(**action.params)
            return bool(result)
        except TypeError as exc:
            logger.error(
                "Action %r called with invalid params %s: %s",
                action.command, action.params, exc,
            )
            return False
        except Exception:
            logger.exception(
                "Unexpected error executing action %r with params %s",
                action.command, action.params,
            )
            return False

    # ------------------------------------------------------------------ #
    # Repr
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        enabled = sum(1 for r in self.rules if r.enabled)
        mode = " [DRY-RUN]" if self.dry_run else ""
        return f"RuleEngine({len(self.rules)} rules, {enabled} enabled{mode})"
