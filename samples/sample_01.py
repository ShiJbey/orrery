import time
from typing import Any, Dict

import orrery.plugins.default.businesses
import orrery.plugins.default.characters
import orrery.plugins.default.names
import orrery.plugins.default.residences
from orrery import Orrery, decorators
from orrery.components.character import CharacterLibrary
from orrery.core.config import OrreryConfig, RelationshipSchema, RelationshipStatConfig
from orrery.core.ecs import Component, GameObject, World
from orrery.core.relationship import Relationship, RelationshipModifier
from orrery.core.social_rule import ISocialRule, SocialRuleLibrary
from orrery.core.status import StatusComponent
from orrery.core.time import SimDateTime
from orrery.core.virtues import Virtues
from orrery.exporter import export_to_json
from orrery.loaders import OrreryYamlLoader, load_all_data
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


@decorators.component(sim)
class Robot(Component):
    """Tags a character as a Robot"""

    pass


class VirtueCompatibilityRule(ISocialRule):
    """
    Determines initial values for romance and friendship
    based on characters' personal virtues
    """

    def get_uid(self) -> str:
        """Return the unique identifier of the modifier"""
        return self.__class__.__name__

    def check_preconditions(self, world: World, *gameobjects: GameObject) -> bool:
        """Return true if a certain condition holds"""
        return all([g.has_component(Virtues) for g in gameobjects])

    def activate(
        self,
        world: World,
        subject: GameObject,
        target: GameObject,
        relationship: GameObject,
    ) -> None:
        """Apply any modifiers associated with the social rule"""
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

        compatibility_mod = RelationshipModifier(
            "virtue-compatibility",
            {"Friendship": friendship_buff, "Romance": romance_buff},
        )

        relationship.get_component(Relationship).add_modifier(compatibility_mod)

    def deactivate(self, relationship: GameObject) -> None:
        """Apply any modifiers associated with the social rule"""
        relationship.get_component(Relationship).remove_modifier_by_uid(
            "virtue-compatibility"
        )


class OwesDebt(StatusComponent):
    """Marks a character as owing money to another character"""

    def __init__(self, created: str, amount: int) -> None:
        super().__init__(created)
        self.amount: int = amount

    def to_dict(self) -> Dict[str, Any]:
        return {"amount": self.amount}


def main():
    """Main entry point for this module"""

    OrreryYamlLoader.from_str(
        """
        Characters:
            - name: "character::robot"
              extends: "character::default"
              components:
                GameCharacter:
                    first_name: "#character::default::first_name::gender-neutral#"
                    last_name: "#character::default::last_name#"
                Robot: {}
        """
    ).load(sim.world, [load_all_data])

    sim.world.get_resource(SocialRuleLibrary).add(VirtueCompatibilityRule())

    character_library = sim.world.get_resource(CharacterLibrary)

    west_world = create_settlement(sim.world, "West World")

    current_date = sim.world.get_resource(SimDateTime)

    delores = create_character(
        sim.world,
        character_library.get_bundle("character::robot"),
        first_name="Delores",
        last_name="Abernathy",
        age=32,
    )

    add_character_to_settlement(delores, west_world)

    charlotte = create_character(
        sim.world,
        character_library.get_bundle("character::default::female"),
        first_name="Charlotte",
        last_name="Hale",
        age=40,
    )

    add_character_to_settlement(charlotte, west_world)

    william = create_character(
        sim.world,
        character_library.get_bundle("character::default::male"),
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
