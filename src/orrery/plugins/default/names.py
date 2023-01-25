import os
import pathlib
from typing import Any

from orrery.core.ecs import World
from orrery.loaders import load_names
from orrery.orrery import Plugin

_RESOURCES_DIR = pathlib.Path(os.path.abspath(__file__)).parent / "data"


class DefaultNameDataPlugin(Plugin):
    def setup(self, world: World, **kwargs: Any) -> None:

        load_names(
            world,
            rule_name="character::default::last_name",
            filepath=_RESOURCES_DIR / "names" / "surnames.txt",
        )

        load_names(
            world,
            rule_name="character::default::first_name::gender-neutral",
            filepath=_RESOURCES_DIR / "names" / "neutral_names.txt",
        )

        load_names(
            world,
            rule_name="character::default::first_name::feminine",
            filepath=_RESOURCES_DIR / "names" / "feminine_names.txt",
        )

        load_names(
            world,
            rule_name="character::default::first_name::masculine",
            filepath=_RESOURCES_DIR / "names" / "masculine_names.txt",
        )

        load_names(
            world,
            rule_name="restaurant_name",
            filepath=_RESOURCES_DIR / "names" / "restaurant_names.txt",
        )

        load_names(
            world,
            rule_name="bar_name",
            filepath=_RESOURCES_DIR / "names" / "bar_names.txt",
        )

        load_names(
            world,
            rule_name="settlement_name",
            filepath=_RESOURCES_DIR / "names" / "US_settlement_names.txt",
        )


def get_plugin() -> Plugin:
    return DefaultNameDataPlugin()
