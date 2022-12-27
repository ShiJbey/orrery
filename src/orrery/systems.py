import random
from collections import Counter
from typing import Any, List

from orrery.components.shared import Actor, FrequentedLocations, Location
from orrery.ecs import ISystem
from orrery.relationship import RelationshipManager
from orrery.utils.common import add_relationship, get_relationship


class MeetNewPeopleSystem(ISystem):
    def process(self, *args: Any, **kwargs: Any):
        for gid, _ in self.world.get_component(Actor):
            character = self.world.get_gameobject(gid)

            frequented_locations = character.get_component(
                FrequentedLocations
            ).locations

            candidates: List[int] = []

            for l in frequented_locations:
                for other_id in (
                    self.world.get_gameobject(l).get_component(Location).frequented_by
                ):
                    candidates.append(other_id)

            if candidates:
                candidate_weights = Counter(candidates)

                # Select one randomly
                options, weights = zip(*candidate_weights.items())

                rng = self.world.get_resource(random.Random)

                acquaintance_id = rng.choices(options, weights=weights, k=1)[0]

                if acquaintance_id not in character.get_component(RelationshipManager):
                    acquaintance = self.world.get_gameobject(acquaintance_id)

                    add_relationship(self.world, character, acquaintance)
                    add_relationship(self.world, acquaintance, character)

                    # Calculate interaction scores
                    get_relationship(
                        self.world, character, acquaintance
                    ).interaction_score += 1
                    get_relationship(
                        self.world, acquaintance, character
                    ).interaction_score += 1
