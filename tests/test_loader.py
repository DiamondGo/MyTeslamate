"""
Unit tests for tesla.scheduler.loader.RuleLoader.
"""

from __future__ import annotations

import textwrap
import pytest
import yaml

from tesla.scheduler.loader import RuleLoader, RuleValidationError
from tesla.scheduler.models import Rule


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _write_yaml(tmp_path, content: str) -> str:
    """Write YAML content to a temp file and return its path."""
    p = tmp_path / "rules.yaml"
    p.write_text(textwrap.dedent(content))
    return str(p)


MINIMAL_VALID_YAML = """
rules:
  - name: "test_rule"
    conditions:
      - field: plugged_in
        operator: eq
        value: true
    actions:
      - command: start_climate
"""

HIGH_TEMP_YAML = """
rules:
  - name: "high_temp_cooling"
    description: "Cool down hot cabin"
    enabled: true
    cooldown_seconds: 600
    trigger_on:
      - INSIDE_TEMP
      - PLUGGED_IN
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
"""


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestRuleLoaderValid:
    """Tests for valid YAML inputs."""

    def test_load_minimal_rule(self, tmp_path):
        path = _write_yaml(tmp_path, MINIMAL_VALID_YAML)
        rules = RuleLoader().load(path)
        assert len(rules) == 1
        rule = rules[0]
        assert rule.name == "test_rule"
        assert rule.enabled is True
        assert rule.cooldown_seconds == 300  # default
        assert len(rule.conditions) == 1
        assert len(rule.actions) == 1

    def test_load_high_temp_rule(self, tmp_path):
        path = _write_yaml(tmp_path, HIGH_TEMP_YAML)
        rules = RuleLoader().load(path)
        assert len(rules) == 1
        rule = rules[0]
        assert rule.name == "high_temp_cooling"
        assert rule.cooldown_seconds == 600
        assert rule.trigger_on == ["INSIDE_TEMP", "PLUGGED_IN"]
        assert len(rule.conditions) == 3
        assert len(rule.actions) == 2

    def test_action_params_loaded(self, tmp_path):
        path = _write_yaml(tmp_path, HIGH_TEMP_YAML)
        rules = RuleLoader().load(path)
        set_temp_action = rules[0].actions[1]
        assert set_temp_action.command == "set_temperature"
        assert set_temp_action.params == {"driver_temp": 22.0}

    def test_disabled_rule_loaded(self, tmp_path):
        yaml_content = """
        rules:
          - name: "disabled_rule"
            enabled: false
            conditions:
              - field: plugged_in
                operator: eq
                value: true
            actions:
              - command: start_climate
        """
        path = _write_yaml(tmp_path, yaml_content)
        rules = RuleLoader().load(path)
        assert rules[0].enabled is False

    def test_multiple_rules_loaded(self, tmp_path):
        yaml_content = """
        rules:
          - name: "rule_one"
            conditions:
              - field: plugged_in
                operator: eq
                value: true
            actions:
              - command: start_climate
          - name: "rule_two"
            conditions:
              - field: inside_temp
                operator: gt
                value: 30.0
            actions:
              - command: stop_climate
        """
        path = _write_yaml(tmp_path, yaml_content)
        rules = RuleLoader().load(path)
        assert len(rules) == 2
        assert rules[0].name == "rule_one"
        assert rules[1].name == "rule_two"

    def test_no_trigger_on_defaults_to_none(self, tmp_path):
        path = _write_yaml(tmp_path, MINIMAL_VALID_YAML)
        rules = RuleLoader().load(path)
        assert rules[0].trigger_on is None

    def test_load_example_rules_file(self):
        """The bundled rules.example.yaml must load without errors."""
        rules = RuleLoader(strict=False).load("rules.example.yaml")
        assert len(rules) >= 2  # at least the two main use cases


class TestRuleLoaderInvalid:
    """Tests for invalid YAML inputs (strict mode)."""

    def test_missing_rules_key(self, tmp_path):
        path = _write_yaml(tmp_path, "something: else\n")
        with pytest.raises(RuleValidationError, match="'rules' is missing"):
            RuleLoader().load(path)

    def test_missing_name(self, tmp_path):
        yaml_content = """
        rules:
          - conditions:
              - field: plugged_in
                operator: eq
                value: true
            actions:
              - command: start_climate
        """
        path = _write_yaml(tmp_path, yaml_content)
        with pytest.raises(RuleValidationError, match="'name' is required"):
            RuleLoader().load(path)

    def test_unknown_condition_field(self, tmp_path):
        yaml_content = """
        rules:
          - name: "bad_rule"
            conditions:
              - field: nonexistent_field
                operator: eq
                value: true
            actions:
              - command: start_climate
        """
        path = _write_yaml(tmp_path, yaml_content)
        with pytest.raises(RuleValidationError, match="does not exist on TeslaState"):
            RuleLoader().load(path)

    def test_unsupported_operator(self, tmp_path):
        yaml_content = """
        rules:
          - name: "bad_rule"
            conditions:
              - field: plugged_in
                operator: contains
                value: true
            actions:
              - command: start_climate
        """
        path = _write_yaml(tmp_path, yaml_content)
        with pytest.raises(RuleValidationError, match="unsupported operator"):
            RuleLoader().load(path)

    def test_unknown_command(self, tmp_path):
        yaml_content = """
        rules:
          - name: "bad_rule"
            conditions:
              - field: plugged_in
                operator: eq
                value: true
            actions:
              - command: fly_to_moon
        """
        path = _write_yaml(tmp_path, yaml_content)
        with pytest.raises(RuleValidationError, match="unknown command"):
            RuleLoader().load(path)

    def test_unknown_trigger_on_event(self, tmp_path):
        yaml_content = """
        rules:
          - name: "bad_rule"
            trigger_on:
              - NOT_A_REAL_EVENT
            conditions:
              - field: plugged_in
                operator: eq
                value: true
            actions:
              - command: start_climate
        """
        path = _write_yaml(tmp_path, yaml_content)
        with pytest.raises(RuleValidationError, match="unknown EventType"):
            RuleLoader().load(path)

    def test_empty_actions_raises(self, tmp_path):
        yaml_content = """
        rules:
          - name: "bad_rule"
            conditions:
              - field: plugged_in
                operator: eq
                value: true
            actions: []
        """
        path = _write_yaml(tmp_path, yaml_content)
        with pytest.raises(RuleValidationError, match="'actions' must not be empty"):
            RuleLoader().load(path)

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            RuleLoader().load("/nonexistent/path/rules.yaml")


class TestRuleLoaderNonStrict:
    """Tests for non-strict mode (skip invalid rules instead of raising)."""

    def test_invalid_rule_skipped_in_non_strict_mode(self, tmp_path):
        yaml_content = """
        rules:
          - name: "good_rule"
            conditions:
              - field: plugged_in
                operator: eq
                value: true
            actions:
              - command: start_climate
          - name: "bad_rule"
            conditions:
              - field: nonexistent_field
                operator: eq
                value: true
            actions:
              - command: start_climate
        """
        path = _write_yaml(tmp_path, yaml_content)
        rules = RuleLoader(strict=False).load(path)
        assert len(rules) == 1
        assert rules[0].name == "good_rule"
