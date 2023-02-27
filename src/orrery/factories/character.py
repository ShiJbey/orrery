from __future__ import annotations

from typing import Any

from orrery.components.character import GameCharacter
from orrery.core.ecs import Component, IComponentFactory, World
from orrery.core.tracery import Tracery


class GameCharacterFactory(IComponentFactory):
    """Constructs instances of GameCharacter components"""

    def create(self, world: World, **kwargs: Any) -> Component:
        name_generator = world.get_resource(Tracery)
        first_name_pattern: str = kwargs["first_name"]
        last_name_pattern: str = kwargs["last_name"]

        age: int = kwargs.get("age", 0)

        first_name = name_generator.generate(first_name_pattern)
        last_name = name_generator.generate(last_name_pattern)

        return GameCharacter(first_name, last_name, age)
