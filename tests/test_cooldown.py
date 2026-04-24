"""
Unit tests for tesla.scheduler.cooldown.CooldownManager.
"""

import pytest
from tesla.scheduler.cooldown import CooldownManager


class TestCooldownManager:
    """Tests for CooldownManager using a controllable clock."""

    def _make_mgr(self, start_time: float = 0.0):
        """Return a CooldownManager with a mutable clock."""
        self._time = start_time
        return CooldownManager(clock=lambda: self._time)

    def _advance(self, seconds: float) -> None:
        self._time += seconds

    # ── can_execute ─────────────────────────────────────────────────── #

    def test_never_executed_can_execute(self):
        mgr = self._make_mgr()
        assert mgr.can_execute("rule_a", cooldown_seconds=300) is True

    def test_just_executed_cannot_execute(self):
        mgr = self._make_mgr()
        mgr.record_execution("rule_a")
        assert mgr.can_execute("rule_a", cooldown_seconds=300) is False

    def test_cooldown_expired_can_execute(self):
        mgr = self._make_mgr()
        mgr.record_execution("rule_a")
        self._advance(301)
        assert mgr.can_execute("rule_a", cooldown_seconds=300) is True

    def test_cooldown_exactly_at_boundary(self):
        mgr = self._make_mgr()
        mgr.record_execution("rule_a")
        self._advance(300)
        # At exactly 300s elapsed, cooldown_seconds=300 → elapsed >= cooldown → allowed
        assert mgr.can_execute("rule_a", cooldown_seconds=300) is True

    def test_cooldown_one_second_short(self):
        mgr = self._make_mgr()
        mgr.record_execution("rule_a")
        self._advance(299)
        assert mgr.can_execute("rule_a", cooldown_seconds=300) is False

    def test_different_rules_independent(self):
        mgr = self._make_mgr()
        mgr.record_execution("rule_a")
        # rule_b has never been executed – should be allowed
        assert mgr.can_execute("rule_b", cooldown_seconds=300) is True
        # rule_a is still in cooldown
        assert mgr.can_execute("rule_a", cooldown_seconds=300) is False

    def test_zero_cooldown_always_allowed(self):
        mgr = self._make_mgr()
        mgr.record_execution("rule_a")
        assert mgr.can_execute("rule_a", cooldown_seconds=0) is True

    # ── record_execution ────────────────────────────────────────────── #

    def test_record_execution_updates_timestamp(self):
        mgr = self._make_mgr(start_time=100.0)
        mgr.record_execution("rule_a")
        self._advance(200)
        # 200s elapsed, cooldown=300 → still in cooldown
        assert mgr.can_execute("rule_a", cooldown_seconds=300) is False
        self._advance(101)
        # 301s total elapsed → allowed
        assert mgr.can_execute("rule_a", cooldown_seconds=300) is True

    def test_re_record_resets_timer(self):
        mgr = self._make_mgr()
        mgr.record_execution("rule_a")
        self._advance(200)
        # Re-execute at t=200
        mgr.record_execution("rule_a")
        self._advance(200)
        # Only 200s since last execution → still in cooldown
        assert mgr.can_execute("rule_a", cooldown_seconds=300) is False

    # ── reset ───────────────────────────────────────────────────────── #

    def test_reset_allows_immediate_execution(self):
        mgr = self._make_mgr()
        mgr.record_execution("rule_a")
        mgr.reset("rule_a")
        assert mgr.can_execute("rule_a", cooldown_seconds=300) is True

    def test_reset_nonexistent_rule_no_error(self):
        mgr = self._make_mgr()
        mgr.reset("nonexistent")  # should not raise

    # ── reset_all ───────────────────────────────────────────────────── #

    def test_reset_all(self):
        mgr = self._make_mgr()
        mgr.record_execution("rule_a")
        mgr.record_execution("rule_b")
        mgr.reset_all()
        assert mgr.can_execute("rule_a", cooldown_seconds=300) is True
        assert mgr.can_execute("rule_b", cooldown_seconds=300) is True

    # ── time_until_ready ────────────────────────────────────────────── #

    def test_time_until_ready_never_executed(self):
        mgr = self._make_mgr()
        assert mgr.time_until_ready("rule_a", cooldown_seconds=300) is None

    def test_time_until_ready_just_executed(self):
        mgr = self._make_mgr()
        mgr.record_execution("rule_a")
        remaining = mgr.time_until_ready("rule_a", cooldown_seconds=300)
        assert remaining == pytest.approx(300.0, abs=1.0)

    def test_time_until_ready_after_cooldown(self):
        mgr = self._make_mgr()
        mgr.record_execution("rule_a")
        self._advance(400)
        remaining = mgr.time_until_ready("rule_a", cooldown_seconds=300)
        assert remaining == 0.0

    # ── repr ────────────────────────────────────────────────────────── #

    def test_repr(self):
        mgr = self._make_mgr()
        mgr.record_execution("rule_a")
        assert "1 rule" in repr(mgr)
