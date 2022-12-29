import os
import pathlib
from typing import Any

from orrery.core.ecs import World
from orrery.core.tracery import Tracery
from orrery.orrery import Plugin

_RESOURCES_DIR = pathlib.Path(os.path.abspath(__file__)).parent / "data"


class DefaultNameDataPlugin(Plugin):
    def setup(self, world: World, **kwargs: Any) -> None:
        # Load entity name data
        name_generator = world.get_resource(Tracery)

        name_generator.load_names(
            rule_name="character::default::last_name",
            filepath=_RESOURCES_DIR / "names" / "surnames.txt",
        )

        name_generator.load_names(
            rule_name="character::default::first_name::gender-neutral",
            filepath=_RESOURCES_DIR / "names" / "neutral_names.txt",
        )

        name_generator.load_names(
            rule_name="character::default::first_name::feminine",
            filepath=_RESOURCES_DIR / "names" / "feminine_names.txt",
        )

        name_generator.load_names(
            rule_name="character::default::first_name::masculine",
            filepath=_RESOURCES_DIR / "names" / "masculine_names.txt",
        )

        # Load potential names for different structures in the town
        name_generator.load_names(
            rule_name="restaurant_name",
            filepath=_RESOURCES_DIR / "names" / "restaurant_names.txt",
        )

        name_generator.load_names(
            rule_name="bar_name", filepath=_RESOURCES_DIR / "names" / "bar_names.txt"
        )

        # Load potential names for the town
        name_generator.load_names(
            rule_name="settlement_name",
            filepath=_RESOURCES_DIR / "names" / "US_settlement_names.txt",
        )


def get_plugin() -> Plugin:
    return DefaultNameDataPlugin()
