"""
CooldownManager – tracks last execution time per rule to enforce cooldown periods.

Prevents the automation system from sending repeated API commands when the same
condition is continuously true (e.g. temperature stays above 40 °C for an hour).

Usage::

    mgr = CooldownManager()

    if mgr.can_execute("high_temp_cooling", cooldown_seconds=600):
        # ... execute actions ...
        mgr.record_execution("high_temp_cooling")
    else:
        logger.debug("Rule 'high_temp_cooling' is in cooldown – skipping.")
"""

from __future__ import annotations

import logging
import time
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class CooldownManager:
    """
    Thread-safe tracker of per-rule last-execution timestamps.

    All times are stored as Unix timestamps (``time.monotonic()``-based for
    reliability across system clock adjustments).

    Parameters
    ----------
    clock:
        Callable returning the current time as a float.  Defaults to
        ``time.monotonic``.  Override in tests to control time.
    """

    def __init__(self, clock=None) -> None:
        self._clock = clock or time.monotonic
        # rule_name → monotonic timestamp of last execution
        self._last_executed: Dict[str, float] = {}

    def can_execute(self, rule_name: str, cooldown_seconds: int) -> bool:
        """
        Return ``True`` when the rule is allowed to execute.

        A rule is allowed when it has never been executed, or when at least
        *cooldown_seconds* have elapsed since the last execution.

        Parameters
        ----------
        rule_name:
            The unique rule identifier (matches :attr:`~tesla.scheduler.models.Rule.name`).
        cooldown_seconds:
            Minimum seconds that must have elapsed since the last execution.
        """
        last = self._last_executed.get(rule_name)
        if last is None:
            return True  # never executed
        elapsed = self._clock() - last
        allowed = elapsed >= cooldown_seconds
        if not allowed:
            remaining = cooldown_seconds - elapsed
            logger.debug(
                "Rule %r is in cooldown (%.0fs remaining of %ds).",
                rule_name, remaining, cooldown_seconds,
            )
        return allowed

    def record_execution(self, rule_name: str) -> None:
        """
        Record that *rule_name* was just executed.

        Call this immediately after successfully dispatching a rule's actions.

        Parameters
        ----------
        rule_name:
            The unique rule identifier.
        """
        self._last_executed[rule_name] = self._clock()
        logger.debug("Cooldown started for rule %r.", rule_name)

    def reset(self, rule_name: str) -> None:
        """
        Clear the cooldown for *rule_name*, allowing it to execute immediately.

        Parameters
        ----------
        rule_name:
            The unique rule identifier.
        """
        self._last_executed.pop(rule_name, None)
        logger.debug("Cooldown reset for rule %r.", rule_name)

    def reset_all(self) -> None:
        """Clear all cooldown records."""
        self._last_executed.clear()
        logger.debug("All cooldowns reset.")

    def time_until_ready(self, rule_name: str, cooldown_seconds: int) -> Optional[float]:
        """
        Return the number of seconds until the rule is ready to execute again.

        Returns ``0.0`` if the rule can execute immediately, or ``None`` if
        the rule has never been executed.

        Parameters
        ----------
        rule_name:
            The unique rule identifier.
        cooldown_seconds:
            The rule's configured cooldown period.
        """
        last = self._last_executed.get(rule_name)
        if last is None:
            return None
        elapsed = self._clock() - last
        remaining = cooldown_seconds - elapsed
        return max(0.0, remaining)

    def __repr__(self) -> str:
        return f"CooldownManager(tracking {len(self._last_executed)} rule(s))"
