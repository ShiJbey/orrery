from __future__ import annotations

from dataclasses import dataclass

from orrery.core.ecs import Component
from orrery.core.time import SimDateTime


@dataclass
class Unemployed(Component):
    """
    Status component that marks a character as being able to work but lacking a job

    Attributes
    ----------
    years: float
        The number of years that the entity has been unemployed
    """

    years: float = 0.0


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
