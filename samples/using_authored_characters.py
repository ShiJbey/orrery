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

from orrery import ISystem, Orrery, OrreryConfig, SimDateTime, TagComponent
from orrery.components import GameCharacter
from orrery.core.relationship import (
    Friendship,
    InteractionScore,
    RelationshipManager,
    Romance,
)
from orrery.core.status import StatusComponent, StatusManager
from orrery.data_collection import DataCollector
from orrery.decorators import component, system
from orrery.exporter import export_to_json
from orrery.utils.common import (
    add_character_to_settlement,
    spawn_character,
    spawn_settlement,
)

sim = Orrery(
    OrreryConfig.parse_obj(
        {
            "seed": 3,
            "relationship_schema": {
                "components": {
                    "Friendship": {
                        "min_value": -100,
                        "max_value": 100,
                    },
                    "Romance": {
                        "min_value": -100,
                        "max_value": 100,
                    },
                    "InteractionScore": {
                        "min_value": -5,
                        "max_value": 5,
                    },
                }
            },
            "plugins": [
                "orrery.plugins.default.names",
                "orrery.plugins.default.characters",
                "orrery.plugins.default.businesses",
                "orrery.plugins.default.residences",
                "orrery.plugins.default.life_events",
                "orrery.plugins.default.ai",
                "orrery.plugins.default.social_rules",
                "orrery.plugins.default.location_bias_rules",
            ],
        }
    )
)


@component(sim)
class Robot(TagComponent):
    """Tags a character as a Robot"""

    pass


@component(sim)
class OwesDebt(StatusComponent):
    """Marks a character as owing money to another character"""

    def __init__(self, amount: int) -> None:
        super().__init__()
        self.amount: int = amount

    def to_dict(self) -> Dict[str, Any]:
        return {**super().to_dict(), "amount": self.amount}


@system(sim)
class RelationshipReporter(ISystem):
    sys_group = "data-collection"

    def process(self, *args: Any, **kwargs: Any) -> None:
        timestamp = self.world.get_resource(SimDateTime).to_iso_str()
        data_collector = self.world.get_resource(DataCollector)
        for guid, (game_character, relationship_manager) in self.world.get_components(
            (GameCharacter, RelationshipManager)
        ):
            if (
                game_character.first_name == "Delores"
                and game_character.last_name == "Abernathy"
            ):
                for target_id, rel_id in relationship_manager.relationships.items():
                    relationship = self.world.get_gameobject(rel_id)
                    data_collector.add_table_row(
                        "relationships",
                        {
                            "timestamp": timestamp,
                            "owner": guid,
                            "target": target_id,
                            "friendship": relationship.get_component(
                                Friendship
                            ).get_value(),
                            "romance": relationship.get_component(Romance).get_value(),
                            "interaction_score": relationship.get_component(
                                InteractionScore
                            ).get_value(),
                            "statuses": str(relationship.get_component(StatusManager)),
                        },
                    )


EXPORT_SIM = False


def main():
    """Main entry point for this module"""
    sim.world.get_resource(DataCollector).create_new_table(
        "relationships",
        (
            "timestamp",
            "owner",
            "target",
            "friendship",
            "romance",
            "interaction_score",
            "statuses",
        ),
    )

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

    st = time.time()
    sim.run_for(25)
    elapsed_time = time.time() - st

    print(f"World Date: {str(sim.world.get_resource(SimDateTime))}")
    print("Execution time: ", elapsed_time, "seconds")

    rel_data = sim.world.get_resource(DataCollector).get_table_dataframe(
        "relationships"
    )

    rel_data[:800].to_csv("rel_data.csv")

    if EXPORT_SIM:
        with open(f"orrery_{sim.config.seed}.json", "w") as f:
            f.write(export_to_json(sim))


if __name__ == "__main__":
    main()
