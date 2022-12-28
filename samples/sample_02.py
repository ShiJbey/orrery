"""
Prototyping the data import pipeline, again.
"""
import pathlib
import random
import yaml
from typing import List, Dict, Any, Optional, Type

from orrery.components.character import CharacterLibrary, GameCharacter
from orrery.core.config import CharacterConfig, OrreryConfig
from orrery.core.ecs import ComponentBundle, Component, World
from orrery.orrery import Orrery
from orrery.utils.common import deep_merge, pprint_gameobject

DATA_PATH = pathlib.Path(__file__).parent / "data" / "data.yaml"


def create_bundle_from_config(world: World, config: CharacterConfig) -> ComponentBundle:
    components: Dict[Type[Component], Dict[str, Any]] = {}

    for c, options in config.components.items():
        component_type = world.get_component_info(c).component_type
        if component_type == GameCharacter:
            components[component_type] = {**options, "config": config.name}
        else:
            components[component_type] = {**options}

    return ComponentBundle(components)

def main():
    sim = Orrery(OrreryConfig())

    library = sim.world.get_resource(CharacterLibrary)

    with open(DATA_PATH, "r") as f:
        data = yaml.safe_load(f)

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
            library.add(config, create_bundle_from_config(sim.world, config))


    chosen = library.choose_random(sim.world.get_resource(random.Random))

    if chosen:
        character = chosen.spawn(sim.world)

        pprint_gameobject(character)


if __name__ == "__main__":
    main()
