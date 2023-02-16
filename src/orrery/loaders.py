"""
orrery/loaders.py

Utility class and functions for importing simulation configuration data
"""
from __future__ import annotations

import pathlib
from typing import Any, Dict, List, Union

import yaml

from orrery.components.business import OccupationType
from orrery.content_management import (
    BusinessLibrary,
    CharacterLibrary,
    OccupationTypeLibrary,
    ResidenceLibrary,
)
from orrery.core.ecs import World
from orrery.core.tracery import Tracery
from orrery.prefabs import BusinessPrefab, CharacterPrefab, ResidencePrefab
from orrery.utils.common import deep_merge


def load_occupation_types(world: World, file_path: Union[str, pathlib.Path]) -> None:
    """Load virtue mappings for activities"""

    path_obj = pathlib.Path(file_path)

    if path_obj.suffix not in (".yaml", ".yml"):
        raise Exception(f"Expected YAML file but file had extension, {path_obj.suffix}")

    with open(file_path, "r") as f:
        data: List[Dict[str, Any]] = yaml.safe_load(f)

    library = world.get_resource(OccupationTypeLibrary)

    for entry in data:
        library.add(
            OccupationType(
                name=entry["name"],
                level=entry.get("level", 1),
            )
        )


def load_character_prefab(world: World, file_path: Union[str, pathlib.Path]) -> None:
    """loads a CharacterEntityPrefab from a yaml file"""

    path_obj = pathlib.Path(file_path)

    if path_obj.suffix not in (".yaml", ".yml"):
        raise Exception(f"Expected YAML file but file had extension, {path_obj.suffix}")

    library = world.get_resource(CharacterLibrary)

    with open(file_path, "r") as f:
        data: Dict[str, Any] = yaml.safe_load(f)

    if "name" not in data:
        raise Exception(f"{file_path} is missing field, 'name'")

    prefab_name = data["name"]

    base_data: Dict[str, Any] = dict()

    if base_prefab_name := data.get("extends", ""):
        base_data = library.get(base_prefab_name).dict()

    full_prefab_data = deep_merge(base_data, data)

    full_prefab_data["components"]["GameCharacter"]["config"] = prefab_name

    if "config" in full_prefab_data:
        full_prefab_data["config"]["name"] = prefab_name
    else:
        full_prefab_data["config"] = {"name": prefab_name}

    new_prefab = CharacterPrefab.parse_obj(full_prefab_data)

    library.add(new_prefab)


def load_business_prefab(world: World, file_path: Union[str, pathlib.Path]) -> None:
    """loads a CharacterEntityPrefab from a yaml file"""

    path_obj = pathlib.Path(file_path)

    if path_obj.suffix not in (".yaml", ".yml"):
        raise Exception(f"Expected YAML file but file had extension, {path_obj.suffix}")

    library = world.get_resource(BusinessLibrary)

    with open(file_path, "r") as f:
        data: Dict[str, Any] = yaml.safe_load(f)

    if "name" not in data:
        raise Exception(f"{file_path} is missing field, 'name'")

    prefab_name = data["name"]

    base_data: Dict[str, Any] = dict()

    if base_prefab_name := data.get("extends", ""):
        base_data = library.get(base_prefab_name).dict()

    full_prefab_data = deep_merge(base_data, data)

    full_prefab_data["components"]["Business"]["config"] = prefab_name

    if "config" in full_prefab_data:
        full_prefab_data["config"]["name"] = prefab_name
    else:
        full_prefab_data["config"] = {"name": prefab_name}

    new_prefab = BusinessPrefab.parse_obj(full_prefab_data)

    library.add(new_prefab)


def load_residence_prefab(world: World, file_path: Union[str, pathlib.Path]) -> None:
    """loads a CharacterEntityPrefab from a yaml file"""

    path_obj = pathlib.Path(file_path)

    if path_obj.suffix not in (".yaml", ".yml"):
        raise Exception(f"Expected YAML file but file had extension, {path_obj.suffix}")

    library = world.get_resource(ResidenceLibrary)

    with open(file_path, "r") as f:
        data: Dict[str, Any] = yaml.safe_load(f)

    if "name" not in data:
        raise Exception(f"{file_path} is missing field, 'name'")

    prefab_name = data["name"]

    base_data: Dict[str, Any] = dict()

    if base_prefab_name := data.get("extends", ""):
        base_data = library.get(base_prefab_name).dict()

    full_prefab_data = deep_merge(base_data, data)

    full_prefab_data["components"]["Residence"]["config"] = prefab_name

    if "config" in full_prefab_data:
        full_prefab_data["config"]["name"] = prefab_name
    else:
        full_prefab_data["config"] = {"name": prefab_name}

    new_prefab = ResidencePrefab.parse_obj(full_prefab_data)

    library.add(new_prefab)


def load_names(
    world: World, rule_name: str, filepath: Union[str, pathlib.Path]
) -> None:
    """Load names a list of names from a text file or given list"""
    tracery_instance = world.get_resource(Tracery)

    with open(filepath, "r") as f:
        tracery_instance.add({rule_name: f.read().splitlines()})
