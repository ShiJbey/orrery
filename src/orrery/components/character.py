from __future__ import annotations

from enum import Enum, IntEnum, auto
from typing import Any, Dict

from orrery.config import CharacterAgingConfig, CharacterConfig
from orrery.core.ecs import Component
from orrery.core.status import StatusComponent
from orrery.core.time import SimDateTime


class Departed(StatusComponent):
    """Tags a character as departed from the simulation"""

    pass


class CanAge(Component):
    """Tags a GameObject as being able to change life stages as time passes"""

    def to_dict(self) -> Dict[str, Any]:
        return {}


class CanDie(Component):
    """Tags a GameObject as being able to die from natural causes"""

    def to_dict(self) -> Dict[str, Any]:
        return {}


class CanGetPregnant(Component):
    """Tags a character as capable of giving birth"""

    def to_dict(self) -> Dict[str, Any]:
        return {}


class Deceased(StatusComponent):
    """Tags a character as deceased"""

    pass


class Retired(StatusComponent):
    """Tags a character as retired"""

    pass


class CollegeGraduate(StatusComponent):
    """Tags a character as having graduated from college"""

    pass


class Gender(Enum):
    Male = auto()
    Female = auto()
    NonBinary = auto()
    NotSpecified = auto()


class LifeStage(IntEnum):
    Child = auto()
    Adolescent = auto()
    YoungAdult = auto()
    Adult = auto()
    Senior = auto()


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
    life_stage: LifeStage
        The current life stage of the character (determined by aging config)
    gender: Gender
        The gender expression of the character
    config: CharacterConfig
        The configuration settings for this character
    """

    __slots__ = "first_name", "last_name", "age", "life_stage", "gender", "config"

    def __init__(
        self,
        config: CharacterConfig,
        first_name: str,
        last_name: str,
        age: int = 0,
        gender: Gender = Gender.NotSpecified,
    ) -> None:
        super().__init__()
        self.config: CharacterConfig = config
        self.first_name: str = first_name
        self.last_name: str = last_name
        self.age: float = float(age)
        self.life_stage: LifeStage = self.life_stage_from_age(
            self.config.aging, int(self.age)
        )
        self.gender: Gender = gender

    @staticmethod
    def life_stage_from_age(aging_config: CharacterAgingConfig, age: int) -> LifeStage:
        """Determine the life stage of a character given an age"""
        if 0 <= age < aging_config.adolescent_age:
            return LifeStage.Child
        elif aging_config.adolescent_age <= age < aging_config.young_adult_age:
            return LifeStage.Adolescent
        elif aging_config.young_adult_age <= age < aging_config.adult_age:
            return LifeStage.YoungAdult
        elif aging_config.adult_age <= age < aging_config.senior_age:
            return LifeStage.Adult
        else:
            return LifeStage.Senior

    @property
    def full_name(self) -> str:
        """Returns the full name of the character"""
        return f"{self.first_name} {self.last_name}"

    def overwrite_age(self, years: float) -> None:
        """Set the characters age"""
        self.age = years

        if self.age >= self.config.aging.senior_age:
            self.life_stage = LifeStage.Senior

        elif self.age >= self.config.aging.adult_age:
            self.life_stage = LifeStage.Adult

        elif self.life_stage >= self.config.aging.young_adult_age:
            self.life_stage = LifeStage.YoungAdult

        elif self.age >= self.config.aging.adolescent_age:
            self.life_stage = LifeStage.Adolescent

        else:
            self.life_stage = LifeStage.Child

    def overwrite_life_stage(self, life_stage: LifeStage) -> None:
        self.life_stage = life_stage

        if life_stage == LifeStage.Senior:
            self.age = self.config.aging.senior_age

        elif life_stage == LifeStage.Adult:
            self.age = self.config.aging.adult_age

        elif life_stage == LifeStage.YoungAdult:
            self.age = self.config.aging.young_adult_age

        elif life_stage == LifeStage.Adolescent:
            self.age = self.config.aging.adolescent_age

        elif life_stage == LifeStage.Child:
            self.age = 0

    def increment_age(self, years: float) -> None:
        """
        Increments the current age of the character, setting the life_stage accordingly

        Parameters
        ----------
        years: float
            The number of years to increment the character's age by
        """
        self.age += years

        if (
            self.life_stage < LifeStage.Adolescent
            and self.age >= self.config.aging.adolescent_age
        ):
            self.life_stage = LifeStage.Adolescent

        elif (
            self.life_stage < LifeStage.YoungAdult
            and self.age >= self.config.aging.young_adult_age
        ):
            self.life_stage = LifeStage.YoungAdult

        elif (
            self.life_stage < LifeStage.Adult
            and self.age >= self.config.aging.adult_age
        ):
            self.life_stage = LifeStage.Adult

        elif (
            self.life_stage < LifeStage.Senior
            and self.age >= self.config.aging.senior_age
        ):
            self.life_stage = LifeStage.Senior

    def to_dict(self) -> Dict[str, Any]:
        return {
            "first_name": self.first_name,
            "last_name": self.last_name,
            "age": self.age,
            "life_stage": self.life_stage.name,
            "gender": self.gender.name,
        }

    def __repr__(self) -> str:
        return "{}({}, age={}, life_stage={}, gender={})".format(
            self.__class__.__name__,
            self.full_name,
            int(self.age),
            self.life_stage.name,
            self.gender.name,
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


class ParentOf(StatusComponent):
    pass


class ChildOf(StatusComponent):
    pass


class SiblingOf(StatusComponent):
    pass


class Married(StatusComponent):
    """Tags two characters as being married"""

    __slots__ = "years"

    def __init__(self, created: str, years: float = 0.0) -> None:
        super().__init__(created)
        self.years: float = years

    def to_dict(self) -> Dict[str, Any]:
        return {**super().to_dict(), "years": self.years}


class Dating(StatusComponent):
    """Tags two characters as dating"""

    __slots__ = "years"

    def __init__(self, created: str, years: float = 0.0) -> None:
        super().__init__(created)
        self.years: float = years

    def to_dict(self) -> Dict[str, Any]:
        return {**super().to_dict(), "years": self.years}
