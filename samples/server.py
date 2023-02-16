from orrery import OrreryConfig
from orrery.config import RelationshipSchema, RelationshipStatConfig
from orrery.content_management import CharacterLibrary
from orrery.data_collection import DataCollector
from orrery.server import OrreryServer
from orrery.utils.common import (
    add_character_to_settlement,
    spawn_character,
    spawn_settlement,
)

app = OrreryServer(
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
        plugins=[
            "orrery.plugins.default.names",
            "orrery.plugins.default.characters",
            # "orrery.plugins.default.businesses",
            # "orrery.plugins.default.residences",
            # "orrery.plugins.default.life_events",
        ],
    )
)


def main():
    character_library = app.sim.world.get_resource(CharacterLibrary)

    west_world = spawn_settlement(app.sim.world, "West World")

    delores = spawn_character(
        app.sim.world,
        character_library.get("character::default::female"),
        first_name="Delores",
        last_name="Abernathy",
        age=32,
    )

    add_character_to_settlement(delores, west_world)

    app.sim.world.get_resource(DataCollector).create_new_table(
        "default", ("pizza", "apples")
    )
    app.sim.world.get_resource(DataCollector).add_table_row(
        "default", {"pizza": 2, "apples": 4}
    )
    app.sim.world.get_resource(DataCollector).add_table_row(
        "default", {"pizza": 87, "apples": 1}
    )
    app.sim.world.get_resource(DataCollector).add_table_row(
        "default", {"pizza": 27, "apples": 53}
    )

    app.run()


if __name__ == "__main__":
    main()
