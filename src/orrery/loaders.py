"""
orrery/loaders.py

Utility class and functions for importing simulation configuration data
"""
from __future__ import annotations

import pathlib
from typing import Any, Dict, List, Protocol, Sequence, Union

import yaml

from orrery.core.config import ActivityToVirtueMap
from orrery.core.ecs import World


class IDataLoader(Protocol):
    """Interface for a function that loads a specific subsection of the YAML data file"""

    def __call__(self, world: World, data: Dict[str, Any]) -> None:
        raise NotImplementedError()


class OrreryYamlLoader:
    """Load Neighborly Component and Archetype definitions from an YAML"""

    __slots__ = "data"

    def __init__(self, data: Dict[str, Any]) -> None:
        self.data: Dict[str, Any] = data

    @classmethod
    def from_path(cls, filepath: Union[str, pathlib.Path]) -> OrreryYamlLoader:
        """Create a new importer instance using a file path"""
        with open(filepath, "r") as f:
            data: Dict[str, Any] = yaml.safe_load(f)
        return cls(data)

    @classmethod
    def from_str(cls, yaml_str: str) -> OrreryYamlLoader:
        """Create a new importer instance using a yaml string"""
        data: Dict[str, Any] = yaml.safe_load(yaml_str)
        return cls(data)

    def load(self, world: World, loaders: Sequence[IDataLoader]) -> None:
        """
        Load each section of that YAML datafile

        Parameters
        ----------
        sim: Simulation
            The simulation instance to load data into
        loaders: Sequence[IDataLoader]
            A function that loads information from the
            yaml data
        """
        for loader in loaders:
            loader(world, self.data)


def load_activity_virtues(world: World, data: Dict[str, Any]) -> None:
    """Load virtue mappings for activities"""
    section_data: Dict[str, List[str]] = data.get("ActivityVirtues", {})

    config = world.get_resource(ActivityToVirtueMap)

    for activity_name, virtue_names in section_data.items():
        config.add_by_name(world, activity_name, *virtue_names)
