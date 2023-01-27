import os
import pathlib
from typing import Any

from orrery.core.ecs import World
from orrery.loaders import load_business_prefab, load_occupation_types
from orrery.orrery import Plugin

_RESOURCES_DIR = pathlib.Path(os.path.abspath(__file__)).parent / "data"


class DefaultBusinessesPlugin(Plugin):
    def setup(self, world: World, **kwargs: Any) -> None:

        load_occupation_types(world, _RESOURCES_DIR / "occupation_types.yaml")

        load_business_prefab(world, _RESOURCES_DIR / "business.default.yaml")
        load_business_prefab(world, _RESOURCES_DIR / "business.default.library.yaml")
        load_business_prefab(world, _RESOURCES_DIR / "business.default.cafe.yaml")


def get_plugin() -> Plugin:
    return DefaultBusinessesPlugin()
