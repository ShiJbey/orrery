import os
import pathlib
from typing import Any

from orrery.core.ecs import World
from orrery.loaders import OrreryYamlLoader, load_character_configs
from orrery.orrery import Plugin

_RESOURCES_DIR = pathlib.Path(os.path.abspath(__file__)).parent / "data"


class DefaultCharactersPlugin(Plugin):
    def setup(self, world: World, **kwargs: Any) -> None:
        OrreryYamlLoader.from_path(_RESOURCES_DIR / "data.yaml").load(
            world, [load_character_configs]
        )


def get_plugin() -> Plugin:
    return DefaultCharactersPlugin()
