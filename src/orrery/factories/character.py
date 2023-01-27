from __future__ import annotations

import random
from typing import Any, Optional

from orrery.components.character import GameCharacter, Gender, LifeStage
from orrery.config import CharacterAgingConfig
from orrery.content_management import CharacterLibrary
from orrery.core.ecs import Component, IComponentFactory, World
from orrery.core.tracery import Tracery


class GameCharacterFactory(IComponentFactory):
    """Constructs instances of GameCharacter components"""

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
        first_name_pattern: str = kwargs["first_name"]
        last_name_pattern: str = kwargs["last_name"]
        config_name: str = kwargs["config"]

        life_stage: Optional[str] = kwargs.get("life_stage")
        age: int = kwargs.get("age", 0)

        config = world.get_resource(CharacterLibrary).get(config_name).config

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
