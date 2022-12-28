import pathlib
from dataclasses import dataclass
from typing import Any, Dict, List

from orrery import Orrery
from orrery.core.activity import ActivityManager
from orrery.components.character import GameCharacter
from orrery.components.shared import Location, Name
from orrery.core.config import OrreryConfig, RelationshipSchema, RelationshipStatConfig
from orrery.core.ecs import Component, ComponentBundle, GameObject, World
from orrery.loaders import OrreryYamlLoader, load_activity_virtues
from orrery.core.relationship import (
    Relationship,
    RelationshipManager,
    RelationshipModifier,
)
from orrery.core.social_rule import SocialRule, SocialRuleLibrary
from orrery.core.status import RelationshipStatusBundle
from orrery.core.traits import Trait, TraitManager
from orrery.utils.common import (
    add_character,
    add_location,
    add_relationship,
    add_relationship_status,
    add_trait,
    get_relationship,
    pprint_gameobject,
)
from orrery.core.virtues import VirtueVector

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


class HumanCharacter(ComponentBundle):
    def __init__(self, first_name: str, last_name: str, age: int) -> None:
        super().__init__(
            {
                GameCharacter: {
                    "first_name": first_name,
                    "last_name": last_name,
                    "age": age,
                },
                RelationshipManager: {},
                TraitManager: {},
                VirtueVector: {},
            }
        )


class RobotCharacter(ComponentBundle):
    def __init__(self, first_name: str, last_name: str, age: int) -> None:
        super().__init__(
            {
                GameCharacter: {
                    "first_name": first_name,
                    "last_name": last_name,
                    "age": age,
                },
                RelationshipManager: {},
                TraitManager: {},
                VirtueVector: {},
                Robot: {},
            }
        )


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

    # Simulation configuration
    config = OrreryConfig(
        relationship_schema=RelationshipSchema(
            stats={
                "Friendship": RelationshipStatConfig(changes_with_time=True),
                "Romance": RelationshipStatConfig(changes_with_time=True),
                "Power": RelationshipStatConfig(min_value=-50, max_value=50, changes_with_time=False),
            }
        )
    )

    sim = Orrery(config)

    sim.world.register_component(Robot)
    sim.world.register_component(InDebt)

    sim.world.get_resource(SocialRuleLibrary).add(VirtueCompatibilityRule())

    OrreryYamlLoader.from_path(
        pathlib.Path(__file__).parent / "data" / "data.yaml"
    ).load(sim.world, [load_activity_virtues])

    add_location(
        sim.world,
        SimpleLocation(
            "The Saloon", ["drinking", "socializing", "cards", "prostitutes"]
        ),
    )

    add_location(
        sim.world, SimpleLocation("The Meadow", ["painting", "fishing", "napping"])
    )

    delores = add_character(
        sim.world,
        RobotCharacter("Delores", "Abernathy", 32),
    )

    charlotte = add_character(
        sim.world,
        HumanCharacter("Charlotte", "Hale", 40),
    )

    william = add_character(
        sim.world,
        HumanCharacter("William", "Black", 68),
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

    pprint_gameobject(delores)

    for c in delores.children:
        pprint_gameobject(c)


if __name__ == "__main__":
    main()
