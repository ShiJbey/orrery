from __future__ import annotations

import random
import re
from enum import Enum, IntEnum, auto
from typing import Any, Dict, List, Optional, Type

from orrery.core.config import CharacterAgingConfig, CharacterConfig
from orrery.core.ecs import Component, ComponentBundle, IComponentFactory, World
from orrery.core.time import SimDateTime
from orrery.core.tracery import Tracery


class Departed(Component):
    """Tags a character as departed from the simulation"""

    pass


class CanAge(Component):
    """
    Tags a GameObject as being able to change life stages as time passes
    """

    pass


class CanDie(Component):
    """
    Tags a GameObject as being able to die from natural causes
    """

    pass


class CanGetPregnant(Component):
    """Tags a character as capable of giving birth"""

    pass


class Deceased(Component):
    """Tags a character as deceased"""

    pass


class Retired(Component):
    """Tags a character as retired"""

    pass


class CollegeGraduate(Component):
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
    __slots__ = "first_name", "last_name", "age", "life_stage", "gender", "config"

    def __init__(
        self,
        config: CharacterConfig,
        first_name: str,
        last_name: str,
        age: int = 0,
        gender: Gender = Gender.NotSpecified,
    ) -> None:
        super(Component, self).__init__()
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
    def name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def increment_age(self, years: float) -> None:
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
        return f"{self.first_name} {self.last_name}"

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"


class GameCharacterFactory(IComponentFactory):
    @staticmethod
    def _generate_age_from_life_stage(
        rng: random.Random, aging_config: CharacterAgingConfig, life_stage: LifeStage
    ) -> int:
        """Return an age for the character given their life_stage"""
        if life_stage == LifeStage.Child:
            return rng.randint(0, aging_config.adolescent_age - 1)
        elif life_stage == LifeStage.Adolescent:
            return rng.randint(
                aging_config.adolescent_age,
                aging_config.young_adult_age - 1,
            )
        elif life_stage == LifeStage.YoungAdult:
            return rng.randint(
                aging_config.young_adult_age,
                aging_config.adult_age - 1,
            )
        elif life_stage == LifeStage.Adult:
            return rng.randint(
                aging_config.adult_age,
                aging_config.senior_age - 1,
            )
        else:
            return aging_config.senior_age + int(10 * rng.random())

    def create(self, world: World, **kwargs: Any) -> Component:
        name_generator = world.get_resource(Tracery)
        first_name_pattern = kwargs["first_name"]
        last_name_pattern = kwargs["last_name"]
        config_name = kwargs["config"]

        life_stage: Optional[str] = kwargs.get("life_stage")
        age: int = kwargs.get("age", 0)

        config = world.get_resource(CharacterLibrary).get(config_name)

        gender_str = kwargs.get("gender", "not-specified").lower()

        gender_options = {
            "man": Gender.Male,
            "male": Gender.Male,
            "female": Gender.Female,
            "woman": Gender.Female,
            "non-binary": Gender.NonBinary,
            "not-specified": Gender.NotSpecified,
        }

        first_name = name_generator.generate(first_name_pattern)
        last_name = name_generator.generate(last_name_pattern)
        gender = gender_options[gender_str]

        if life_stage is not None:
            # LifeStage overwrites any given age
            age = self._generate_age_from_life_stage(
                world.get_resource(random.Random), config.aging, LifeStage[life_stage]
            )

        return GameCharacter(config, first_name, last_name, gender=gender, age=age)


class CharacterComponentBundle(ComponentBundle):

    __slots__ = "name"

    def __init__(
        self, name: str, components: Dict[Type[Component], Dict[str, Any]]
    ) -> None:
        super().__init__(components)
        self.name: str = name


class CharacterLibrary:
    """Collection of factories that create character entities"""

    __slots__ = "_configs", "_bundles"

    def __init__(self) -> None:
        self._configs: Dict[str, CharacterConfig] = {}
        self._bundles: Dict[str, CharacterComponentBundle] = {}

    def add(
        self, config: CharacterConfig, bundle: Optional[CharacterComponentBundle] = None
    ) -> None:
        """Register a new archetype by name"""
        self._configs[config.name] = config
        if bundle:
            self._bundles[config.name] = bundle

    def get_all(self) -> List[CharacterConfig]:
        """Get all stored archetypes"""
        return list(self._configs.values())

    def get(self, name: str) -> CharacterConfig:
        """Get an archetype by name"""
        return self._configs[name]

    def get_bundle(self, name: str) -> CharacterComponentBundle:
        """Retrieve the ComponentBundle mapped to the given name"""
        return self._bundles[name]

    def get_matching_bundles(
        self, *bundle_names: str
    ) -> List[CharacterComponentBundle]:
        """Get all component bundles that match the given regex strings"""

        matches: List[CharacterComponentBundle] = []

        for name, bundle in self._bundles.items():
            if any([re.match(pattern, name) for pattern in bundle_names]):
                matches.append(bundle)

        return matches

    def choose_random(
        self,
        rng: random.Random,
    ) -> Optional[CharacterComponentBundle]:
        """Performs a weighted random selection across all character archetypes"""
        choices: List[CharacterConfig] = []
        weights: List[int] = []

        for config in self.get_all():
            if config.template is False:
                choices.append(config)
                weights.append(config.spawning.spawn_frequency)

        if choices:
            # Choose an archetype at random
            chosen_config = rng.choices(population=choices, weights=weights, k=1)[0]

            return self._bundles[chosen_config.name]
        else:
            return None


class Pregnant(Component):
    """
    Pregnant characters give birth when the timeout
    """

    __slots__ = "partner_id", "due_date"

    def __init__(self, partner_id: int, due_date: SimDateTime) -> None:
        super(Component, self).__init__()
        self.partner_id: int = partner_id
        self.due_date: SimDateTime = due_date
