from __future__ import annotations

from typing import Any, Dict, List, Tuple

from orrery.core.ecs import GameObject
from orrery.core.event import Event
from orrery.core.roles import RoleInstance
from orrery.core.time import SimDateTime


class JoinSettlementEvent(Event):

    __slots__ = "settlement", "character"

    def __init__(
        self,
        date: SimDateTime,
        settlement: GameObject,
        character: GameObject,
    ) -> None:
        super().__init__(timestamp=date)
        self.settlement: GameObject = settlement
        self.character: GameObject = character

    def to_dict(self) -> Dict[str, Any]:
        return {
            **super().to_dict(),
            "settlement": self.settlement.uid,
            "character": self.character.uid,
        }

    def __str__(self) -> str:
        return (
            super().__str__()
            + f" Settlement: {self.settlement}, "
            + f"Character: {self.character}"
        )


class LeaveSettlementEvent(Event):

    __slots__ = "settlement", "character"

    def __init__(
        self, date: SimDateTime, settlement: GameObject, character: GameObject
    ) -> None:
        super().__init__(timestamp=date)
        self.settlement: GameObject = settlement
        self.character: GameObject = character

    def to_dict(self) -> Dict[str, Any]:
        return {
            **super().to_dict(),
            "settlement": self.settlement.uid,
            "character": self.character.uid,
        }

    def __str__(self) -> str:
        return (
            super().__str__()
            + f"Settlement: {self.settlement}"
            + f"Character: {self.character}"
        )


class ChildBirthEvent(Event):
    def __init__(
        self,
        date: SimDateTime,
        birthing_parent: GameObject,
        other_parent: GameObject,
        child: GameObject,
    ) -> None:
        super().__init__(
            name="ChildBirth",
            timestamp=date,
            roles=[
                RoleInstance("BirthingParent", birthing_parent.uid),
                RoleInstance("OtherParent", other_parent.uid),
                RoleInstance("Child", child.uid),
            ],
        )


class DeathEvent(Event):
    def __init__(self, date: SimDateTime, character: GameObject) -> None:
        super().__init__(date)
        self.character: GameObject = character


class DepartEvent(Event):
    def __init__(
        self, date: SimDateTime, characters: List[GameObject], reason: str
    ) -> None:
        super().__init__(date)
        self.characters: List[GameObject] = characters
        self.reason = reason

    def to_dict(self) -> Dict[str, Any]:
        return {**super().to_dict(), "reason": self.reason}

    def __str__(self) -> str:
        return f"{super().__str__()}, reason={self.reason}"


class MoveIntoTownEvent(Event):
    def __init__(
        self, date: SimDateTime, residence: GameObject, *characters: GameObject
    ) -> None:
        super().__init__(date)
        self.characters: Tuple[GameObject, ...] = characters
        self.residence: GameObject = residence


class MoveResidenceEvent(Event):
    def __init__(self, date: SimDateTime, *characters: GameObject) -> None:
        super().__init__(date)
        self.characters: Tuple[GameObject, ...] = characters


class BusinessClosedEvent(Event):
    def __init__(self, date: SimDateTime, business: GameObject) -> None:
        super().__init__(date)
        self.business: GameObject = business


class BirthEvent(Event):
    def __init__(self, date: SimDateTime, character: GameObject) -> None:
        super().__init__(date)
        self.character: GameObject = character


class GiveBirthEvent(Event):
    def __init__(
        self,
        date: SimDateTime,
        birthing_parent: GameObject,
        other_parent: GameObject,
        baby: GameObject,
    ) -> None:
        super().__init__(
            name="GiveBirth",
            timestamp=date,
            roles=[
                RoleInstance("BirthingParent", birthing_parent.uid),
                RoleInstance("OtherParent", other_parent.uid),
                RoleInstance("Baby", baby.uid),
            ],
        )


class PregnantEvent(Event):
    def __init__(
        self,
        date: SimDateTime,
        pregnant_one: GameObject,
        partner: GameObject,
    ) -> None:
        super().__init__(
            name="Pregnant",
            timestamp=date,
            roles=[
                RoleInstance("PregnantOne", pregnant_one.uid),
                RoleInstance("Partner", partner.uid),
            ],
        )


class StartJobEvent(Event):
    __slots__ = "occupation"

    def __init__(
        self,
        date: SimDateTime,
        character: GameObject,
        business: GameObject,
        occupation: str,
    ) -> None:
        super().__init__(
            name="StartJob",
            timestamp=date,
            roles=[
                RoleInstance("Business", business.uid),
                RoleInstance("Character", character.uid),
            ],
        )
        self.occupation: str = occupation

    def to_dict(self) -> Dict[str, Any]:
        return {
            **super().to_dict(),
            "occupation": self.occupation,
        }

    def __str__(self) -> str:
        return f"{super().__str__()}, occupation={self.occupation}"


class EndJobEvent(Event):
    __slots__ = "occupation", "reason"

    def __init__(
        self,
        date: SimDateTime,
        character: GameObject,
        business: GameObject,
        occupation: str,
        reason: str,
    ) -> None:
        super().__init__(
            name="LeaveJob",
            timestamp=date,
            roles=[
                RoleInstance("Business", business.uid),
                RoleInstance("Character", character.uid),
            ],
        )
        self.occupation: str = occupation
        self.reason: str = reason

    def to_dict(self) -> Dict[str, Any]:
        return {
            **super().to_dict(),
            "occupation": self.occupation,
            "reason": self.reason,
        }

    def __str__(self) -> str:
        return (
            f"{super().__str__()}, occupation={self.occupation}, reason={self.reason}"
        )


class MarriageEvent(Event):
    def __init__(
        self,
        date: SimDateTime,
        *characters: GameObject,
    ) -> None:
        super().__init__(
            name="Marriage",
            timestamp=date,
            roles=[RoleInstance("Character", c.uid) for c in characters],
        )


class DivorceEvent(Event):
    def __init__(
        self,
        date: SimDateTime,
        *characters: GameObject,
    ) -> None:
        super().__init__(
            name="Divorce",
            timestamp=date,
            roles=[RoleInstance("Character", c.uid) for c in characters],
        )


class StartBusinessEvent(Event):
    __slots__ = "occupation", "business_name"

    def __init__(
        self,
        date: SimDateTime,
        character: GameObject,
        business: GameObject,
        occupation: str,
        business_name: str,
    ) -> None:
        super().__init__(
            name="StartBusiness",
            timestamp=date,
            roles=[
                RoleInstance("Business", business.uid),
                RoleInstance("Character", character.uid),
            ],
        )
        self.occupation: str = occupation
        self.business_name: str = business_name

    def to_dict(self) -> Dict[str, Any]:
        return {
            **super().to_dict(),
            "occupation": self.occupation,
            "business_name": self.business_name,
        }

    def __str__(self) -> str:
        return f"{super().__str__()}, business_name={self.business_name}, occupation={self.occupation}"


class BusinessOpenEvent(Event):
    def __init__(
        self,
        date: SimDateTime,
        business: GameObject,
        business_name: str,
    ) -> None:
        super().__init__(date)
        self.business: GameObject = business
        self.business_name: str = business_name

    def to_dict(self) -> Dict[str, Any]:
        return {
            **super().to_dict(),
            "business_name": self.business_name,
        }

    def __str__(self) -> str:
        return f"{super().__str__()}, business_name={self.business_name}"


class NewSettlementEvent(Event):

    __slots__ = "settlement"

    def __init__(
        self,
        date: SimDateTime,
        settlement: GameObject,
    ) -> None:
        super().__init__(timestamp=date)
        self.settlement: GameObject = settlement

    def __str__(self) -> str:
        return f"{super().__str__()} Settlement: {self.settlement}"


class NewCharacterEvent(Event):

    __slots__ = "character"

    def __init__(
        self,
        date: SimDateTime,
        character: GameObject,
    ) -> None:
        super().__init__(timestamp=date)
        self.character: GameObject = character

    def __str__(self) -> str:
        return f"{super().__str__()} Character: {self.character}"


class NewBusinessEvent(Event):
    def __init__(
        self,
        date: SimDateTime,
        business: GameObject,
    ) -> None:
        super().__init__(date)
        self.business: GameObject = business

    def __str__(self) -> str:
        return f"{super().__str__()} Business: {self.business}"


class NewResidenceEvent(Event):
    def __init__(
        self,
        date: SimDateTime,
        residence: GameObject,
    ) -> None:
        super().__init__(date)
        self.residence: GameObject = residence

    def __str__(self) -> str:
        return f"{super().__str__()} Residence: {self.residence}"


class BecomeAdolescentEvent(Event):
    def __init__(
        self,
        date: SimDateTime,
        character: GameObject,
    ) -> None:
        super().__init__(date)
        self.character: GameObject = character

    def __str__(self) -> str:
        return f"{super().__str__()} Character: {self.character}"


class BecomeYoungAdultEvent(Event):
    def __init__(
        self,
        date: SimDateTime,
        character: GameObject,
    ) -> None:
        super().__init__(date)
        self.character: GameObject = character

    def __str__(self) -> str:
        return f"{super().__str__()} Character: {self.character}"


class BecomeAdultEvent(Event):
    def __init__(
        self,
        date: SimDateTime,
        character: GameObject,
    ) -> None:
        super().__init__(date)
        self.character: GameObject = character

    def __str__(self) -> str:
        return f"{super().__str__()} Character: {self.character}"


class BecomeSeniorEvent(Event):
    def __init__(
        self,
        date: SimDateTime,
        character: GameObject,
    ) -> None:
        super().__init__(date)
        self.character: GameObject = character

    def __str__(self) -> str:
        return f"{super().__str__()} Character: {self.character}"


class RetirementEvent(Event):
    __slots__ = "occupation"

    def __init__(
        self,
        date: SimDateTime,
        character: GameObject,
        business: GameObject,
        occupation: str,
    ) -> None:
        super().__init__(date)
        self.character: GameObject = character
        self.business: GameObject = business
        self.occupation: str = occupation

    def to_dict(self) -> Dict[str, Any]:
        return {
            **super().to_dict(),
            "occupation": self.occupation,
        }
