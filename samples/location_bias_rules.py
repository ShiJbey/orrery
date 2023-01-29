"""
samples/location_bias_rules.py

This sample shows how location bias rules are used to create probability distribution
of where a character may frequent within a town. LocationBiasRules are can be imported
from plugins and authored within the same script.
"""
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from orrery import Component, GameObject, Orrery
from orrery.components import Location
from orrery.content_management import ActivityLibrary
from orrery.core.location_bias import ILocationBiasRule
from orrery.utils.common import score_location

sim = Orrery()


@sim.component()
@dataclass
class Actor(Component):
    name: str

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name}


@sim.component()
class SocialButterfly(Component):
    def to_dict(self) -> Dict[str, Any]:
        return {}


@sim.component()
class HealthNut(Component):
    def to_dict(self) -> Dict[str, Any]:
        return {}


@sim.component()
class BookWorm(Component):
    def to_dict(self) -> Dict[str, Any]:
        return {}


@sim.component()
class RecoveringAlcoholic(Component):
    def to_dict(self) -> Dict[str, Any]:
        return {}


@sim.component()
class Shopaholic(Component):
    def to_dict(self) -> Dict[str, Any]:
        return {}


@sim.location_bias_rule()
class SocialButterflyLocationBias(ILocationBiasRule):
    def get_rule_name(self) -> str:
        return "social-butterfly"

    def check_location(self, location: GameObject) -> bool:
        return (
            location.world.get_resource(ActivityLibrary).get("Socializing")
            in location.get_component(Location).activities
        )

    def check_character(self, character: GameObject) -> bool:
        return character.has_component(SocialButterfly)

    def evaluate(self, character: GameObject, location: GameObject) -> int:
        return 2


@sim.location_bias_rule()
class RecoveringAlcoholicLocationBias(ILocationBiasRule):
    def get_rule_name(self) -> str:
        return "recovering-alcoholic"

    def check_location(self, location: GameObject) -> bool:
        return (
            location.world.get_resource(ActivityLibrary).get("Drinking")
            in location.get_component(Location).activities
        )

    def check_character(self, character: GameObject) -> bool:
        return character.has_component(RecoveringAlcoholic)

    def evaluate(self, character: GameObject, location: GameObject) -> int:
        return -3


@sim.location_bias_rule()
class ShopaholicLocationBias(ILocationBiasRule):
    def get_rule_name(self) -> str:
        return "shop-alcoholic"

    def check_location(self, location: GameObject) -> bool:
        return (
            location.world.get_resource(ActivityLibrary).get("Shopping")
            in location.get_component(Location).activities
        )

    def check_character(self, character: GameObject) -> bool:
        return character.has_component(Shopaholic)

    def evaluate(self, character: GameObject, location: GameObject) -> int:
        return 3


@sim.location_bias_rule()
class BookWormLocationBias(ILocationBiasRule):
    def get_rule_name(self) -> str:
        return "book-worm"

    def check_location(self, location: GameObject) -> bool:
        return (
            location.world.get_resource(ActivityLibrary).get("Reading")
            in location.get_component(Location).activities
        )

    def check_character(self, character: GameObject) -> bool:
        return character.has_component(BookWorm)

    def evaluate(self, character: GameObject, location: GameObject) -> int:
        return 2


@sim.location_bias_rule()
class HealthNutLocationBias(ILocationBiasRule):
    def get_rule_name(self) -> str:
        return "health-nut"

    def check_location(self, location: GameObject) -> bool:
        return (
            location.world.get_resource(ActivityLibrary).get("Recreation")
            in location.get_component(Location).activities
        )

    def check_character(self, character: GameObject) -> bool:
        return character.has_component(HealthNut)

    def evaluate(self, character: GameObject, location: GameObject) -> int:
        return 2


def calculate_location_probabilities(
    character: GameObject, locations: List[GameObject]
) -> List[Tuple[float, GameObject]]:
    """Calculate the probability distribution for a character and set of locations"""

    score_total: int = 0
    scores: List[Tuple[float, GameObject]] = []

    # Score each location
    for loc in locations:
        score = score_location(character, loc)
        score_total += math.exp(score)
        scores.append((math.exp(score), loc))

    # Perform softmax
    probabilities = [(score / score_total, loc) for score, loc in scores]

    # Sort
    probabilities.sort(key=lambda pair: pair[0], reverse=True)

    return probabilities


def main():

    ###############################
    # SPAWN NEW LOCATIONS
    ###############################

    locations = [
        sim.world.spawn_gameobject(
            [
                Location(
                    activities={
                        sim.world.get_resource(ActivityLibrary).get("Recreation"),
                        sim.world.get_resource(ActivityLibrary).get("Socializing"),
                    }
                )
            ],
            name="Gym",
        ),
        sim.world.spawn_gameobject(
            [
                Location(
                    activities={
                        sim.world.get_resource(ActivityLibrary).get("Reading"),
                    }
                )
            ],
            name="Library",
        ),
        sim.world.spawn_gameobject(
            [
                Location(
                    activities={
                        sim.world.get_resource(ActivityLibrary).get("Shopping"),
                        sim.world.get_resource(ActivityLibrary).get("Socializing"),
                        sim.world.get_resource(ActivityLibrary).get("People Watching"),
                    }
                )
            ],
            name="Mall",
        ),
        sim.world.spawn_gameobject(
            [
                Location(
                    activities={
                        sim.world.get_resource(ActivityLibrary).get("Drinking"),
                        sim.world.get_resource(ActivityLibrary).get("Socializing"),
                    }
                )
            ],
            name="Bar",
        ),
    ]

    characters = [
        sim.world.spawn_gameobject([Actor("Alice"), HealthNut(), SocialButterfly()]),
        sim.world.spawn_gameobject(
            [Actor("James"), Shopaholic(), BookWorm(), HealthNut()]
        ),
        sim.world.spawn_gameobject(
            [Actor("Raven"), RecoveringAlcoholic(), HealthNut(), SocialButterfly()]
        ),
    ]

    for c in characters:
        # Score all the locations in the map
        probs = calculate_location_probabilities(c, locations)
        print(f"== {c.get_component(Actor).name} ==")
        print([(loc.name, prob) for prob, loc in probs])


if __name__ == "__main__":
    main()
