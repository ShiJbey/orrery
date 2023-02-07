from __future__ import annotations

from typing import Any, Dict, List

from orrery.core.ecs import GameObject
from orrery.core.event import Event, RoleInstance
from orrery.core.time import SimDateTime


class JoinSettlementEvent(Event):
    def __init__(
        self,
        date: SimDateTime,
        settlement: GameObject,
        character: GameObject,
    ) -> None:
        super().__init__(
            name="JoinSettlement",
            timestamp=date.to_iso_str(),
            roles=[
                RoleInstance("Settlement", settlement.uid),
                RoleInstance("Character", character.uid),
            ],
        )


class LeaveSettlementEvent(Event):
    def __init__(
        self, date: SimDateTime, settlement: GameObject, character: GameObject
    ) -> None:
        super().__init__(
            name="LeaveSettlement",
            timestamp=date.to_iso_str(),
            roles=[
                RoleInstance("Settlement", settlement.uid),
                RoleInstance("Character", character.uid),
            ],
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
            timestamp=date.to_iso_str(),
            roles=[
                RoleInstance("BirthingParent", birthing_parent.uid),
                RoleInstance("OtherParent", other_parent.uid),
                RoleInstance("Child", child.uid),
            ],
        )


class DeathEvent(Event):
    def __init__(self, date: SimDateTime, character: GameObject) -> None:
        super().__init__(
            name="Death",
            timestamp=date.to_iso_str(),
            roles=[
                RoleInstance("Character", character.uid),
            ],
        )


class DepartEvent(Event):
    def __init__(
        self, date: SimDateTime, characters: List[GameObject], reason: str
    ) -> None:
        super().__init__(
            name="Depart",
            timestamp=date.to_iso_str(),
            roles=[RoleInstance("Character", c.uid) for c in characters],
        )
        self.reason = reason

    def to_dict(self) -> Dict[str, Any]:
        return {**super().to_dict(), "reason": self.reason}

    def __str__(self) -> str:
        return f"{super().__str__()}, reason={self.reason}"


class MoveIntoTownEvent(Event):
    def __init__(
        self, date: SimDateTime, residence: GameObject, *characters: GameObject
    ) -> None:
        super().__init__(
            name="MoveIntoTown",
            timestamp=date.to_iso_str(),
            roles=[
                RoleInstance("Residence", residence.uid),
                *[RoleInstance("Character", c.uid) for c in characters],
            ],
        )


class MoveResidenceEvent(Event):
    def __init__(self, date: SimDateTime, *characters: GameObject) -> None:
        super().__init__(
            name="MoveResidence",
            timestamp=date.to_iso_str(),
            roles=[RoleInstance("Character", c.uid) for c in characters],
        )


class BusinessClosedEvent(Event):
    def __init__(self, date: SimDateTime, business: GameObject) -> None:
        super().__init__(
            name="BusinessClosed",
            timestamp=date.to_iso_str(),
            roles=[
                RoleInstance("Business", business.uid),
            ],
        )


class BirthEvent(Event):
    def __init__(self, date: SimDateTime, character: GameObject) -> None:
        super().__init__(
            name="Birth",
            timestamp=date.to_iso_str(),
            roles=[RoleInstance("Character", character.uid)],
        )


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
            timestamp=date.to_iso_str(),
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
            timestamp=date.to_iso_str(),
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
            timestamp=date.to_iso_str(),
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
            timestamp=date.to_iso_str(),
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
            timestamp=date.to_iso_str(),
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
            timestamp=date.to_iso_str(),
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
            timestamp=date.to_iso_str(),
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
    __slots__ = "business_name"

    def __init__(
        self,
        date: SimDateTime,
        business: GameObject,
        business_name: str,
    ) -> None:
        super().__init__(
            name="business-open",
            timestamp=date.to_iso_str(),
            roles=[
                RoleInstance("Business", business.uid),
            ],
        )
        self.business_name: str = business_name

    def to_dict(self) -> Dict[str, Any]:
        return {
            **super().to_dict(),
            "business_name": self.business_name,
        }

    def __str__(self) -> str:
        return f"{super().__str__()}, business_name={self.business_name}"


class NewSettlementEvent(Event):
    def __init__(
        self,
        date: SimDateTime,
        settlement: GameObject,
    ) -> None:
        super().__init__(
            name="new-settlement",
            timestamp=date.to_iso_str(),
            roles=[
                RoleInstance("Settlement", settlement.uid),
            ],
        )


class NewCharacterEvent(Event):
    def __init__(
        self,
        date: SimDateTime,
        character: GameObject,
    ) -> None:
        super().__init__(
            name="new-character",
            timestamp=date.to_iso_str(),
            roles=[
                RoleInstance("Character", character.uid),
            ],
        )


class NewBusinessEvent(Event):
    def __init__(
        self,
        date: SimDateTime,
        business: GameObject,
    ) -> None:
        super().__init__(
            name="new-business",
            timestamp=date.to_iso_str(),
            roles=[
                RoleInstance("Business", business.uid),
            ],
        )


class NewResidenceEvent(Event):
    def __init__(
        self,
        date: SimDateTime,
        residence: GameObject,
    ) -> None:
        super().__init__(
            name="new-residence",
            timestamp=date.to_iso_str(),
            roles=[
                RoleInstance("Residence", residence.uid),
            ],
        )


class BecomeAdolescentEvent(Event):
    def __init__(
        self,
        date: SimDateTime,
        character: GameObject,
    ) -> None:
        super().__init__(
            name="BecomeAdolescent",
            timestamp=date.to_iso_str(),
            roles=[
                RoleInstance("Character", character.uid),
            ],
        )


class BecomeYoungAdultEvent(Event):
    def __init__(
        self,
        date: SimDateTime,
        character: GameObject,
    ) -> None:
        super().__init__(
            name="BecomeYoungAdult",
            timestamp=date.to_iso_str(),
            roles=[
                RoleInstance("Character", character.uid),
            ],
        )


class BecomeAdultEvent(Event):
    def __init__(
        self,
        date: SimDateTime,
        character: GameObject,
    ) -> None:
        super().__init__(
            name="BecomeAdult",
            timestamp=date.to_iso_str(),
            roles=[
                RoleInstance("Character", character.uid),
            ],
        )


class BecomeSeniorEvent(Event):
    def __init__(
        self,
        date: SimDateTime,
        character: GameObject,
    ) -> None:
        super().__init__(
            name="BecomeSenior",
            timestamp=date.to_iso_str(),
            roles=[
                RoleInstance("Character", character.uid),
            ],
        )


class RetirementEvent(Event):
    __slots__ = "occupation"

    def __init__(
        self,
        date: SimDateTime,
        character: GameObject,
        business: GameObject,
        occupation: str,
    ) -> None:
        super().__init__(
            name="LeaveJob",
            timestamp=date.to_iso_str(),
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
