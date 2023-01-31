import os
import pathlib

from orrery.loaders import load_residence_prefab
from orrery.orrery import Orrery, PluginInfo

_RESOURCES_DIR = pathlib.Path(os.path.abspath(__file__)).parent / "data"

plugin_info: PluginInfo = {
    "name": "default residences plugin",
    "plugin_id": "default.residences",
    "version": "0.1.0",
}


def setup(sim: Orrery):
    load_residence_prefab(sim.world, _RESOURCES_DIR / "residence.default.house.yaml")
