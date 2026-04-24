"""
Unit tests for tesla.scheduler.models.Condition.evaluate()
"""

import pytest
from tesla.scheduler.models import Condition, SUPPORTED_OPERATORS


class TestConditionEvaluate:
    """Tests for Condition.evaluate() with all supported operators."""

    # ── eq ──────────────────────────────────────────────────────────── #

    def test_eq_true(self):
        assert Condition("f", "eq", True).evaluate(True) is True

    def test_eq_false_mismatch(self):
        assert Condition("f", "eq", True).evaluate(False) is False

    def test_eq_string(self):
        assert Condition("f", "eq", "Home").evaluate("Home") is True

    def test_eq_string_mismatch(self):
        assert Condition("f", "eq", "Home").evaluate("Work") is False

    def test_eq_none(self):
        assert Condition("f", "eq", None).evaluate(None) is True

    # ── ne ──────────────────────────────────────────────────────────── #

    def test_ne_true(self):
        assert Condition("f", "ne", "Home").evaluate("Work") is True

    def test_ne_false_same(self):
        assert Condition("f", "ne", "Home").evaluate("Home") is False

    # ── gt / gte ────────────────────────────────────────────────────── #

    def test_gt_above(self):
        assert Condition("f", "gt", 40.0).evaluate(42.5) is True

    def test_gt_equal(self):
        assert Condition("f", "gt", 40.0).evaluate(40.0) is False

    def test_gt_below(self):
        assert Condition("f", "gt", 40.0).evaluate(38.0) is False

    def test_gt_none_actual(self):
        # None actual value should return False for numeric comparisons.
        assert Condition("f", "gt", 40.0).evaluate(None) is False

    def test_gte_equal(self):
        assert Condition("f", "gte", 40.0).evaluate(40.0) is True

    def test_gte_above(self):
        assert Condition("f", "gte", 40.0).evaluate(41.0) is True

    def test_gte_below(self):
        assert Condition("f", "gte", 40.0).evaluate(39.9) is False

    # ── lt / lte ────────────────────────────────────────────────────── #

    def test_lt_below(self):
        assert Condition("f", "lt", 20).evaluate(15) is True

    def test_lt_equal(self):
        assert Condition("f", "lt", 20).evaluate(20) is False

    def test_lte_equal(self):
        assert Condition("f", "lte", 20).evaluate(20) is True

    def test_lte_above(self):
        assert Condition("f", "lte", 20).evaluate(21) is False

    # ── in / not_in ─────────────────────────────────────────────────── #

    def test_in_present(self):
        assert Condition("f", "in", ["Stopped", "Disconnected"]).evaluate("Stopped") is True

    def test_in_absent(self):
        assert Condition("f", "in", ["Stopped", "Disconnected"]).evaluate("Charging") is False

    def test_not_in_absent(self):
        assert Condition("f", "not_in", ["Home", "Work"]).evaluate("Mall") is True

    def test_not_in_present(self):
        assert Condition("f", "not_in", ["Home", "Work"]).evaluate("Home") is False

    # ── is_none / not_none ──────────────────────────────────────────── #

    def test_is_none_true(self):
        assert Condition("f", "is_none").evaluate(None) is True

    def test_is_none_false(self):
        assert Condition("f", "is_none").evaluate(42) is False

    def test_not_none_true(self):
        assert Condition("f", "not_none").evaluate("something") is True

    def test_not_none_false(self):
        assert Condition("f", "not_none").evaluate(None) is False

    # ── validation ──────────────────────────────────────────────────── #

    def test_invalid_operator_raises(self):
        with pytest.raises(ValueError, match="Unsupported operator"):
            Condition("f", "contains", "x")

    def test_all_operators_accepted(self):
        """Every operator in SUPPORTED_OPERATORS should construct without error."""
        for op in SUPPORTED_OPERATORS:
            Condition("f", op, None)  # should not raise


class TestConditionRepr:
    def test_repr(self):
        c = Condition("inside_temp", "gt", 40.0)
        assert "inside_temp" in repr(c)
        assert "gt" in repr(c)
        assert "40.0" in repr(c)
