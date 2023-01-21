from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from orrery.core.ecs import Component
from orrery.core.time import SimDateTime


class Unemployed(Component):
    """
    Status component that marks a character as being able to work but lacking a job

    Attributes
    ----------
    days_to_find_a_job: int
        The number of remaining days to find a job
    grace_period: int
        The starting number of days to find a job
    """

    __slots__ = "days_to_find_a_job", "grace_period"

    def __init__(self, days_to_find_a_job: int) -> None:
        super().__init__()
        self.days_to_find_a_job: int = days_to_find_a_job
        self.grace_period: int = days_to_find_a_job

    def to_dict(self) -> Dict[str, Any]:
        return {
            **super().to_dict(),
            "days_to_find_a_job": self.days_to_find_a_job,
            "grace_period": self.grace_period,
        }


class Pregnant(Component):
    """
    Pregnant characters give birth to new child characters after the due_date

    Attributes
    ----------
    partner_id: int
        The GameObject ID of the character that impregnated this character
    due_date: SimDateTime
        The date that the baby is due
    """

    __slots__ = "partner_id", "due_date"

    def __init__(self, partner_id: int, due_date: SimDateTime) -> None:
        super().__init__()
        self.partner_id: int = partner_id
        self.due_date: SimDateTime = due_date


class InTheWorkforce(Component):
    """Tags a character as being eligible to work"""

    pass


class BossOf(Component):
    pass


class EmployeeOf(Component):
    pass


class CoworkerOf(Component):
    pass


class ParentOf(Component):
    pass


class ChildOf(Component):
    pass


class SiblingOf(Component):
    pass


@dataclass
class Married(Component):
    """Tags two characters as being married"""

    years: float = 0


@dataclass
class Dating(Component):
    """Tags two characters as dating"""

    years: float = 0
