from dataclasses import dataclass
from typing import Any, Dict, List

import orrery.plugins.default.businesses
import orrery.plugins.default.characters
import orrery.plugins.default.life_events
import orrery.plugins.default.names
import orrery.plugins.default.residences
from orrery import Orrery
from orrery.components.business import BusinessLibrary
from orrery.components.character import CharacterLibrary
from orrery.components.shared import Location, Name
from orrery.core.activity import ActivityManager
from orrery.core.config import OrreryConfig, RelationshipSchema, RelationshipStatConfig
from orrery.core.ecs import Component, ComponentBundle, GameObject, World
from orrery.core.relationship import Relationship, RelationshipModifier
from orrery.core.social_rule import SocialRule, SocialRuleLibrary
from orrery.core.status import RelationshipStatusBundle
from orrery.core.traits import Trait
from orrery.core.virtues import VirtueVector
from orrery.loaders import OrreryYamlLoader, load_all_data
from orrery.utils.common import (
    add_business,
    add_character,
    add_relationship,
    add_relationship_status,
    add_trait,
    create_business,
    create_character,
    create_settlement,
    get_relationship,
)

#######################################
# Sample Components
#######################################


class Robot(Component):
    pass


#######################################
# Traits
#######################################


hates_robots = Trait(
    "Hates Robots",
    [
        SocialRule(
            "Hates Robots",
            lambda world, *gameobjects: gameobjects[1].has_component(Robot),
            [RelationshipModifier("", {"Friendship": -5, "Romance": -9})],
        )
    ],
)


#######################################
# Main Application
#######################################


class SimpleLocation(ComponentBundle):
    def __init__(self, name: str, activities: List[str]) -> None:
        super().__init__(
            {
                Name: {"name": name},
                Location: {},
                ActivityManager: {"activities": activities},
            }
        )


class VirtueCompatibilityRule:
    """
    Determines initial values for romance and friendship
    based on characters' personal virtues
    """

    def get_uid(self) -> str:
        """Return the unique identifier of the modifier"""
        return self.__class__.__name__

    def check_preconditions(self, world: World, *gameobjects: GameObject) -> bool:
        """Return true if a certain condition holds"""
        return all([g.has_component(VirtueVector) for g in gameobjects])

    def activate(
        self,
        world: World,
        subject: GameObject,
        target: GameObject,
        relationship: Relationship,
    ) -> None:
        """Apply any modifiers associated with the social rule"""
        character_virtues = subject.get_component(VirtueVector)
        acquaintance_virtues = target.get_component(VirtueVector)

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

        relationship.add_modifier(compatibility_mod)

    def deactivate(self, relationship: Relationship) -> None:
        """Apply any modifiers associated with the social rule"""
        relationship.remove_modifier_by_uid("virtue-compatibility")


@dataclass
class InDebt(Component):
    amount: int

    def to_dict(self) -> Dict[str, Any]:
        return {"amount": self.amount}


class InDeptStatus(RelationshipStatusBundle):
    def __init__(self, owner: int, target: int, amount: int) -> None:
        super().__init__(owner, target, (InDebt, {"amount": amount}))


def main():
    """Main entry point for this module"""
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
    sim.load_plugin(orrery.plugins.default.life_events.get_plugin())

    sim.world.register_component(Robot)
    sim.world.register_component(InDebt)

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
    business_library = sim.world.get_resource(BusinessLibrary)

    west_world = create_settlement(sim.world, "West World")

    add_business(
        sim.world,
        create_business(sim.world, business_library.get_bundle("Library")),
        west_world,
    )

    add_business(
        sim.world,
        create_business(sim.world, business_library.get_bundle("Library")),
        west_world,
    )

    add_business(
        sim.world,
        create_business(sim.world, business_library.get_bundle("Library")),
        west_world,
    )

    add_business(
        sim.world,
        create_business(sim.world, business_library.get_bundle("Library")),
        west_world,
    )

    delores = add_character(
        sim.world,
        create_character(
            sim.world,
            character_library.get_bundle("character::robot"),
            first_name="Delores",
            last_name="Abernathy",
            age=32,
        ),
    )

    charlotte = add_character(
        sim.world,
        create_character(
            sim.world,
            character_library.get_bundle("character::default::female"),
            first_name="Charlotte",
            last_name="Hale",
            age=40,
        ),
    )

    william = add_character(
        sim.world,
        create_character(
            sim.world,
            character_library.get_bundle("character::default::male"),
            first_name="William",
            age=68,
        ),
    )

    add_relationship(sim.world, delores, charlotte)
    get_relationship(sim.world, delores, charlotte)["Friendship"] += -1
    get_relationship(sim.world, delores, charlotte)["Friendship"] += 1

    add_relationship_status(
        sim.world, delores, InDeptStatus(delores.id, charlotte.id, 500)
    )

    add_relationship(sim.world, delores, william)
    get_relationship(sim.world, delores, william)["Romance"] += 4
    get_relationship(sim.world, delores, william)["Romance"] += -7
    get_relationship(sim.world, delores, william)["Interaction"] += 1

    add_relationship(sim.world, william, delores)["Interaction"] += 1
    add_trait(sim.world, william, hates_robots)

    TIMESTEPS = 12

    for _ in range(TIMESTEPS):
        sim.world.step()

    print()


if __name__ == "__main__":
    main()
