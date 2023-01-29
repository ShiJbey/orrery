#!/usr/bin/env python3
"""
samples/sample_01.py

Sample of
"""
import time
from typing import Any, Dict

import orrery.plugins.default.businesses
import orrery.plugins.default.characters
import orrery.plugins.default.names
import orrery.plugins.default.residences
from orrery import Orrery
from orrery.components.virtues import Virtues
from orrery.config import OrreryConfig, RelationshipSchema, RelationshipStatConfig
from orrery.content_management import CharacterLibrary
from orrery.core.ecs import Component, GameObject
from orrery.core.social_rule import ISocialRule
from orrery.core.status import StatusComponent
from orrery.core.time import SimDateTime
from orrery.exporter import export_to_json
from orrery.utils.common import (
    add_character_to_settlement,
    create_character,
    create_settlement,
)
from orrery.utils.relationships import (
    add_relationship,
    add_relationship_status,
    get_relationship,
)

sim = Orrery(
    OrreryConfig(
        seed=3,
        relationship_schema=RelationshipSchema(
            stats={
                "Friendship": RelationshipStatConfig(changes_with_time=True),
                "Romance": RelationshipStatConfig(changes_with_time=True),
                "Power": RelationshipStatConfig(
                    min_value=-50, max_value=50, changes_with_time=False
                ),
            }
        ),
    )
)

sim.load_plugin(orrery.plugins.default.names.get_plugin())
sim.load_plugin(orrery.plugins.default.characters.get_plugin())
sim.load_plugin(orrery.plugins.default.businesses.get_plugin())
sim.load_plugin(orrery.plugins.default.residences.get_plugin())


@sim.component()
class Robot(Component):
    """Tags a character as a Robot"""

    def to_dict(self) -> Dict[str, Any]:
        return {}


@sim.component()
class OwesDebt(StatusComponent):
    """Marks a character as owing money to another character"""

    def __init__(self, created: str, amount: int) -> None:
        super().__init__(created)
        self.amount: int = amount

    def to_dict(self) -> Dict[str, Any]:
        return {"amount": self.amount}


@sim.social_rule()
class VirtueCompatibilityRule(ISocialRule):
    """
    Determines initial values for romance and friendship
    based on characters' personal virtues
    """

    def get_rule_name(self) -> str:
        """Return the unique identifier of the modifier"""
        return self.__class__.__name__

    def check_target(self, gameobject: GameObject) -> bool:
        """Return true if a certain condition holds"""
        return gameobject.has_component(Virtues)

    def check_initiator(self, gameobject: GameObject) -> bool:
        """Return true if a certain condition holds"""
        return gameobject.has_component(Virtues)

    def evaluate(self, initiator: GameObject, target: GameObject) -> Dict[str, int]:
        """Apply any modifiers associated with the social rule"""
        character_virtues = initiator.get_component(Virtues)
        acquaintance_virtues = target.get_component(Virtues)

        compatibility = character_virtues.compatibility(acquaintance_virtues)

        romance_buff: int = 0
        friendship_buff: int = 0

        if compatibility < -0.5:
            romance_buff = -2
            friendship_buff = -3
        elif compatibility < 0:
            romance_buff = -1
            friendship_buff = -2
        elif compatibility > 0:
            romance_buff = 1
            friendship_buff = 2
        elif compatibility > 0.5:
            romance_buff = 2
            friendship_buff = 3

        return {"Friendship": friendship_buff, "Romance": romance_buff}


def main():
    """Main entry point for this module"""

    character_library = sim.world.get_resource(CharacterLibrary)

    west_world = create_settlement(sim.world, "West World")

    current_date = sim.world.get_resource(SimDateTime)

    delores = create_character(
        sim.world,
        character_library.get("character::default::female"),
        first_name="Delores",
        last_name="Abernathy",
        age=32,
    )

    delores.add_component(Robot())

    add_character_to_settlement(delores, west_world)

    charlotte = create_character(
        sim.world,
        character_library.get("character::default::female"),
        first_name="Charlotte",
        last_name="Hale",
        age=40,
    )

    add_character_to_settlement(charlotte, west_world)

    william = create_character(
        sim.world,
        character_library.get("character::default::male"),
        first_name="William",
        age=68,
    )

    add_character_to_settlement(william, west_world)

    add_relationship(delores, charlotte)
    get_relationship(delores, charlotte)["Friendship"] += -1
    get_relationship(delores, charlotte)["Friendship"] += 1

    add_relationship_status(
        delores, charlotte, OwesDebt(current_date.to_iso_str(), 500)
    )

    add_relationship(delores, william)
    get_relationship(delores, william)["Romance"] += 4
    get_relationship(delores, william)["Romance"] += -7
    get_relationship(delores, william)["Interaction"] += 1

    add_relationship(william, delores)
    get_relationship(william, delores)["Interaction"] += 1

    st = time.time()
    sim.run_for(100)
    elapsed_time = time.time() - st

    print(f"World Date: {str(sim.world.get_resource(SimDateTime))}")
    print("Execution time: ", elapsed_time, "seconds")

    with open(f"orrery_{sim.config.seed}.json", "w") as f:
        f.write(export_to_json(sim))


if __name__ == "__main__":
    main()
