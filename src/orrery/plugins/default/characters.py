import os
import pathlib
from typing import Any

from orrery.core.ecs import World
from orrery.loaders import load_character_prefab
from orrery.orrery import Plugin

_RESOURCES_DIR = pathlib.Path(os.path.abspath(__file__)).parent / "data"


class DefaultCharactersPlugin(Plugin):
    def setup(self, world: World, **kwargs: Any) -> None:
        load_character_prefab(world, _RESOURCES_DIR / "character.default.yaml")
        load_character_prefab(world, _RESOURCES_DIR / "character.default.male.yaml")
        load_character_prefab(world, _RESOURCES_DIR / "character.default.female.yaml")
        load_character_prefab(
            world, _RESOURCES_DIR / "character.default.non-binary.yaml"
        )


def get_plugin() -> Plugin:
    return DefaultCharactersPlugin()
