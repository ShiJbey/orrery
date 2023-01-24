from __future__ import annotations

from typing import Any, Dict

from orrery.core.status import StatusComponent
from orrery.core.time import SimDateTime


class Unemployed(StatusComponent):
    """
    Status component that marks a character as being able to work but lacking a job

    Attributes
    ----------
    years: float
        The number of years that the entity has been unemployed
    """

    __slots__ = "years"

    def __init__(self, created: str, years: int = 0.0) -> None:
        super().__init__(created)
        self.years: float = years

    def to_dict(self) -> Dict[str, Any]:
        return {**super().to_dict(), "years": self.years}


class Pregnant(StatusComponent):
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

    def __init__(self, created: str, partner_id: int, due_date: SimDateTime) -> None:
        super().__init__(created)
        self.partner_id: int = partner_id
        self.due_date: SimDateTime = due_date

    def to_dict(self) -> Dict[str, Any]:
        return {
            **super().to_dict(),
            "partner_id": self.partner_id,
            "due_date": self.due_date.to_iso_str(),
        }


class InTheWorkforce(StatusComponent):
    """Tags a character as being eligible to work"""

    pass


class BossOf(StatusComponent):
    pass


class EmployeeOf(StatusComponent):
    pass


class CoworkerOf(StatusComponent):
    pass


class ParentOf(StatusComponent):
    pass


class ChildOf(StatusComponent):
    pass


class SiblingOf(StatusComponent):
    pass


class Married(StatusComponent):
    """Tags two characters as being married"""

    __slots__ = "years"

    def __init__(self, created: str, years: int = 0.0) -> None:
        super().__init__(created)
        self.years: float = years

    def to_dict(self) -> Dict[str, Any]:
        return {**super().to_dict(), "years": self.years}


class Dating(StatusComponent):
    """Tags two characters as dating"""

    __slots__ = "years"

    def __init__(self, created: str, years: int = 0.0) -> None:
        super().__init__(created)
        self.years: float = years

    def to_dict(self) -> Dict[str, Any]:
        return {**super().to_dict(), "years": self.years}
