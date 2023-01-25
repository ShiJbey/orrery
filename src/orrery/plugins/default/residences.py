import os
import pathlib
from typing import Any

from orrery.core.ecs import World
from orrery.loaders import load_residence_prefab
from orrery.orrery import Plugin

_RESOURCES_DIR = pathlib.Path(os.path.abspath(__file__)).parent / "data"


class DefaultResidencesPlugin(Plugin):
    def setup(self, world: World, **kwargs: Any) -> None:
        load_residence_prefab(world, _RESOURCES_DIR / "residence.default.house.yaml")


def get_plugin() -> Plugin:
    return DefaultResidencesPlugin()
