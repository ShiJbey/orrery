from __future__ import annotations

import dataclasses
from abc import ABC
from inspect import isclass
from typing import Any, Dict, List, Type, Union

from orrery.core.ecs import Component, TagComponent
from orrery.core.status import StatusComponent
from orrery.core.time import SimDateTime


class Departed(StatusComponent):
    """Tags a character as departed from the simulation"""

    is_persistent = True


class CanAge(TagComponent):
    """Tags a GameObject as being able to change life stages as time passes"""

    pass


class CanDie(TagComponent):
    """Tags a GameObject as being able to die from natural causes"""

    pass


class CanGetPregnant(TagComponent):
    """Tags a character as capable of giving birth"""

    pass


class Deceased(StatusComponent):
    """Tags a character as deceased"""

    is_persistent = True


class Retired(StatusComponent):
    """Tags a character as retired"""

    # is_persistent = True


class CollegeGraduate(StatusComponent):
    """Tags a character as having graduated from college"""

    # is_persistent = True


class GameCharacter(Component):
    """
    This component is attached to all GameObjects that are characters in the simulation

    Attributes
    ----------
    first_name: str
        The character's first name
    last_name: str
        The character's last or family name
    age: float
        The age of the character in years
    """

    __slots__ = "first_name", "last_name", "age"

    def __init__(
        self,
        first_name: str,
        last_name: str,
        age: int = 0,
    ) -> None:
        super().__init__()
        self.first_name: str = first_name
        self.last_name: str = last_name
        self.age: float = float(age)

    @property
    def full_name(self) -> str:
        """Returns the full name of the character"""
        return f"{self.first_name} {self.last_name}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "first_name": self.first_name,
            "last_name": self.last_name,
            "age": self.age,
        }

    def __repr__(self) -> str:
        return "{}(name={}, age={})".format(
            self.__class__.__name__,
            self.full_name,
            int(self.age),
        )

    def __str__(self) -> str:
        return self.full_name


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

    def __init__(self, partner_id: int, due_date: SimDateTime) -> None:
        super().__init__()
        self.partner_id: int = partner_id
        self.due_date: SimDateTime = due_date

    def to_dict(self) -> Dict[str, Any]:
        return {
            **super().to_dict(),
            "partner_id": self.partner_id,
            "due_date": self.due_date.to_iso_str(),
        }


class ParentOf(StatusComponent):
    pass


class ChildOf(StatusComponent):
    pass


class SiblingOf(StatusComponent):
    pass


class Married(StatusComponent):
    """Tags two characters as being married"""

    __slots__ = "years"

    def __init__(self, years: float = 0.0) -> None:
        super().__init__()
        self.years: float = years

    def to_dict(self) -> Dict[str, Any]:
        return {**super().to_dict(), "years": self.years}


class Dating(StatusComponent):
    """Tags two characters as dating"""

    __slots__ = "years"

    def __init__(self, years: float = 0.0) -> None:
        super().__init__()
        self.years: float = years

    def to_dict(self) -> Dict[str, Any]:
        return {**super().to_dict(), "years": self.years}


@dataclasses.dataclass()
class MarriageConfig(Component):
    spouse_prefabs: List[str] = dataclasses.field(default_factory=list)
    chance_spawn_with_spouse: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chance_spawn_with_spouse": self.chance_spawn_with_spouse,
            "spouse_prefabs": self.spouse_prefabs,
        }


@dataclasses.dataclass()
class AgingConfig(Component):
    lifespan: int
    adolescent_age: int
    young_adult_age: int
    adult_age: int
    senior_age: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lifespan": self.lifespan,
            "adolescent_age": self.adolescent_age,
            "young_adult_age": self.young_adult_age,
            "adult_age": self.adult_age,
            "senior_age": self.senior_age,
        }


@dataclasses.dataclass()
class ReproductionConfig(Component):
    max_children_at_spawn: int = 3
    child_prefabs: List[str] = dataclasses.field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_children_at_spawn": self.max_children_at_spawn,
            "child_prefabs": self.child_prefabs,
        }


class Gender(TagComponent, ABC):
    pass


class Male(TagComponent):
    pass


class Female(TagComponent):
    pass


class NonBinary(TagComponent):
    pass


class LifeStage(StatusComponent, ABC):

    is_persistent = True
    _value: int

    def __int__(self) -> int:
        return self.value()

    @classmethod
    def value(cls) -> int:
        return cls._value

    def __eq__(self, other: Union[object, int, Type[LifeStage]]) -> bool:
        if isinstance(other, int):
            return self.value() == other
        if isinstance(other, LifeStage):
            return self.value() == other.value()
        if isclass(other) and issubclass(other, LifeStage):
            return self.value() == other.value()
        raise TypeError(f"Expected type of LifeStage or int, but was {other}")

    def __ge__(self, other: Union[object, int, Type[LifeStage]]) -> bool:
        if isinstance(other, int):
            return self.value() >= other
        if isinstance(other, LifeStage):
            return self.value() >= other.value()
        if isclass(other) and issubclass(other, LifeStage):
            return self.value() >= other.value()
        raise TypeError(f"Expected type of LifeStage or int, but was {other}")

    def __le__(self, other: Union[object, int, Type[LifeStage]]) -> bool:
        if isinstance(other, int):
            return self.value() <= other
        if isinstance(other, LifeStage):
            return self.value() <= other.value()
        if isclass(other) and issubclass(other, LifeStage):
            return self.value() <= other.value()
        raise TypeError(f"Expected type of LifeStage or int, but was {other}")

    def __gt__(self, other: Union[object, int, Type[LifeStage]]) -> bool:
        if isinstance(other, int):
            return self.value() > other
        if isinstance(other, LifeStage):
            return self.value() > other.value()
        if isclass(other) and issubclass(other, LifeStage):
            return self.value() > other.value()
        raise TypeError(f"Expected type of LifeStage ot int, but was {other}")

    def __lt__(self, other: Union[object, int, Type[LifeStage]]) -> bool:
        if isinstance(other, int):
            return self.value() < other
        if isinstance(other, LifeStage):
            return self.value() < other.value()
        if isclass(other) and issubclass(other, LifeStage):
            return self.value() < other.value()
        raise TypeError(f"Expected type of LifeStage or int, but was {other}")


class Child(LifeStage):

    _value = 0


class Adolescent(LifeStage):
    _value = 1


class YoungAdult(LifeStage):
    _value = 2


class Adult(LifeStage):
    _value = 3


class Senior(LifeStage):
    _value = 4
