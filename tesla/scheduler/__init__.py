"""
Tesla automation scheduler package.

Provides:
  - Condition: a single field/operator/value predicate evaluated against TeslaState
  - Action: a controller command to execute when conditions are met
  - Rule: a named automation rule combining conditions + actions + metadata
  - CooldownManager: tracks last execution time per rule to enforce cooldown periods
  - RuleLoader: loads and validates Rule objects from a YAML file
  - RuleEngine: evaluates rules against TeslaState and dispatches actions
"""

from tesla.scheduler.models import Condition, Action, Rule
from tesla.scheduler.cooldown import CooldownManager
from tesla.scheduler.loader import RuleLoader
from tesla.scheduler.engine import RuleEngine

__all__ = [
    "Condition",
    "Action",
    "Rule",
    "CooldownManager",
    "RuleLoader",
    "RuleEngine",
]
