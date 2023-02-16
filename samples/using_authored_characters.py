#!/usr/bin/env python3
"""
This sample shows how to construct a social simulation model manually, It starts with
creating a simulation instance from configuration settings. Next, we use decorator
methods to register new components (Robot, OwesDebt) and a social rule. Finally, within
the main function, we define a new settlement, add new characters, and set some
relationship values.
"""
import time
from typing import Any, Dict

from orrery import Component, GameObject, Orrery, OrreryConfig, SimDateTime
from orrery.components import Virtues
from orrery.core.status import StatusComponent
from orrery.exporter import export_to_json
from orrery.utils.common import (
    add_character_to_settlement,
    spawn_business,
    spawn_character,
    spawn_settlement,
    start_job,
)
from orrery.utils.relationships import (
    add_relationship,
    add_relationship_status,
    get_relationship,
)

sim = Orrery(
    OrreryConfig.parse_obj(
        {
            "seed": 3,
            "relationship_schema": {
                "stats": {
                    "Friendship": {
                        "min_value": -100,
                        "max_value": 100,
                        "changes_with_time": True,
                    },
                    "Romance": {
                        "min_value": -100,
                        "max_value": 100,
                        "changes_with_time": True,
                    },
                },
            },
            "plugins": [
                "orrery.plugins.default.names",
                "orrery.plugins.default.characters",
                "orrery.plugins.default.businesses",
                "orrery.plugins.default.residences",
                "orrery.plugins.default.life_events",
            ],
        }
    )
)


@sim.component()
class Robot(Component):
    """Tags a character as a Robot"""

    def to_dict(self) -> Dict[str, Any]:
        return {}


@sim.component()
class OwesDebt(StatusComponent):
    """Marks a character as owing money to another character"""

    def __init__(self, amount: int) -> None:
        super().__init__()
        self.amount: int = amount

    def to_dict(self) -> Dict[str, Any]:
        return {"amount": self.amount}


@sim.social_rule("virtue compatibility")
def rule(subject: GameObject, target: GameObject) -> Dict[str, int]:
    if not subject.has_component(Virtues):
        return {}

    if not target.has_component(Virtues):
        return {}

    character_virtues = subject.get_component(Virtues)
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

    west_world = spawn_settlement(sim.world, "West World")

    delores = spawn_character(
        sim.world,
        "character::default::female",
        first_name="Delores",
        last_name="Abernathy",
        age=32,
    )

    delores.add_component(Robot())

    add_character_to_settlement(delores, west_world)

    charlotte = spawn_character(
        sim.world,
        "character::default::female",
        first_name="Charlotte",
        last_name="Hale",
        age=40,
    )

    add_character_to_settlement(charlotte, west_world)

    william = spawn_character(
        sim.world,
        "character::default::male",
        first_name="William",
        last_name="ManInBlack",
        age=68,
    )

    add_character_to_settlement(william, west_world)

    cafe = spawn_business(sim.world, "business::default::cafe", "Starbucks - WW")

    start_job(delores, cafe, "Owner", is_owner=True)

    add_relationship(delores, charlotte)
    get_relationship(delores, charlotte)["Friendship"] += -1
    get_relationship(delores, charlotte)["Friendship"] += 1

    add_relationship_status(delores, charlotte, OwesDebt(500))

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
