"""
orrery/loaders.py

Utility class and functions for importing simulation configuration data
"""
from __future__ import annotations

import pathlib
from typing import Any, Dict, List, Optional, Protocol, Sequence, Type, Union

import yaml

from orrery.components.business import (
    Business,
    BusinessLibrary,
    OccupationType,
    OccupationTypeLibrary,
)
from orrery.components.character import CharacterLibrary, GameCharacter
from orrery.components.residence import (
    Residence,
    ResidenceComponentBundle,
    ResidenceLibrary,
)
from orrery.core.activity import ActivityToVirtueMap
from orrery.core.config import BusinessConfig, CharacterConfig, ResidenceConfig
from orrery.core.ecs import Component, ComponentBundle, World
from orrery.utils.common import deep_merge


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


def load_occupation_types(world: World, data: Dict[str, Any]) -> None:
    """Load virtue mappings for activities"""
    library = world.get_resource(OccupationTypeLibrary)

    section_data: List[Dict[str, Any]] = data.get("Occupations", [])

    for entry in section_data:
        library.add(
            OccupationType(
                name=entry["name"],
                level=entry.get("level", 1),
                description=entry.get("description", ""),
            )
        )


def load_character_configs(world: World, data: Dict[str, Any]) -> None:
    """Load virtue mappings for activities"""
    library = world.get_resource(CharacterLibrary)

    section_data: List[Dict[str, Any]] = data.get("Characters", [])

    for entry in section_data:

        is_template: bool = entry.get("template", False)
        extends: Optional[str] = entry.get("extends", None)

        base_data: Dict[str, Any] = dict()

        if extends:
            base_data = library.get(extends).dict()

        config_data = deep_merge(base_data, entry)

        config = CharacterConfig.parse_obj(config_data)

        config.template = is_template

        if is_template:
            library.add(config)
        else:
            library.add(config, create_character_bundle(world, config))


def load_business_configs(world: World, data: Dict[str, Any]) -> None:
    """Load virtue mappings for activities"""
    library = world.get_resource(BusinessLibrary)

    section_data: List[Dict[str, Any]] = data.get("Businesses", [])

    for entry in section_data:

        is_template: bool = entry.get("template", False)
        extends: Optional[str] = entry.get("extends", None)

        base_data: Dict[str, Any] = dict()

        if extends:
            base_data = library.get(extends).dict()

        config_data = deep_merge(base_data, entry)

        config = BusinessConfig.parse_obj(config_data)

        config.template = is_template

        if is_template:
            library.add(config)
        else:
            library.add(config, create_business_bundle(world, config))


def load_residence_configs(world: World, data: Dict[str, Any]) -> None:
    """Load virtue mappings for activities"""
    library = world.get_resource(ResidenceLibrary)

    section_data: List[Dict[str, Any]] = data.get("Residences", [])

    for entry in section_data:

        is_template: bool = entry.get("template", False)
        extends: Optional[str] = entry.get("extends", None)

        base_data: Dict[str, Any] = dict()

        if extends:
            base_data = library.get(extends).dict()

        config_data = deep_merge(base_data, entry)

        config = ResidenceConfig.parse_obj(config_data)

        config.template = is_template

        if is_template:
            library.add(config)
        else:
            library.add(config, create_residence_bundle(world, config))


def load_all_data(world: World, data: Dict[str, Any]) -> None:
    load_activity_virtues(world, data)
    load_character_configs(world, data)
    load_business_configs(world, data)
    load_residence_configs(world, data)
    load_occupation_types(world, data)


def create_character_bundle(world: World, config: CharacterConfig) -> ComponentBundle:
    components: Dict[Type[Component], Dict[str, Any]] = {}

    for c, options in config.components.items():
        component_type = world.get_component_info(c).component_type
        if component_type == GameCharacter:
            components[component_type] = {**options, "config": config.name}
        else:
            components[component_type] = {**options}

    return ComponentBundle(components)


def create_business_bundle(world: World, config: BusinessConfig) -> ComponentBundle:
    components: Dict[Type[Component], Dict[str, Any]] = {}

    for c, options in config.components.items():
        component_type = world.get_component_info(c).component_type
        if component_type == Business:
            components[component_type] = {**options, "config": config.name}
        else:
            components[component_type] = {**options}

    return ComponentBundle(components)


def create_residence_bundle(
    world: World, config: ResidenceConfig
) -> ResidenceComponentBundle:
    components: Dict[Type[Component], Dict[str, Any]] = {}

    unit_components: Dict[Type[Component], Dict[str, Any]] = {}

    for c, options in config.components.items():
        component_type = world.get_component_info(c).component_type
        if component_type == Residence:
            components[component_type] = {**options, "config": config.name}
        else:
            components[component_type] = {**options}

    for c, options in config.unit_components.items():
        component_type = world.get_component_info(c).component_type
        unit_components[component_type] = {**options}

    return ResidenceComponentBundle(
        building_components=components,
        unit_components=unit_components,
        units=config.num_units,
    )
