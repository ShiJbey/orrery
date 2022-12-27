from __future__ import annotations

import random
from orrery.activity import ActivityLibrary, ActivityManager, ActivityManagerFactory


from orrery.components.shared import Actor, Location, Name
from orrery.config import ActivityToVirtueConfig, OrreryConfig

from orrery.ecs import World
from orrery.relationship import RelationshipManager, UpdateRelationshipsSystem
from orrery.social_rule import SocialRuleLibrary
from orrery.status import RelationshipStatus, StatusDuration, statusDurationSystem
from orrery.systems import MeetNewPeopleSystem
from orrery.tracery import Tracery
from orrery.traits import TraitManager
from orrery.virtues import VirtueVector, VirtueVectorFactory


class Orrery:

    __slots__ = "world"

    def __init__(self, config: OrreryConfig) -> None:
        self.world: World = World()

        # Add default resources
        self.world.add_resource(config)
        self.world.add_resource(Tracery)
        self.world.add_resource(random.Random(config.seed))
        self.world.add_resource(SocialRuleLibrary())
        self.world.add_resource(ActivityLibrary())
        self.world.add_resource(ActivityToVirtueConfig())

        # Add default systems
        self.world.add_system(statusDurationSystem())
        self.world.add_system(UpdateRelationshipsSystem())
        self.world.add_system(MeetNewPeopleSystem())

        # Register components
        self.world.register_component(Actor)
        self.world.register_component(Name)
        self.world.register_component(RelationshipManager)
        self.world.register_component(TraitManager)
        self.world.register_component(Location)
        self.world.register_component(VirtueVector, factory=VirtueVectorFactory())
        self.world.register_component(ActivityManager, factory=ActivityManagerFactory())
        self.world.register_component(RelationshipStatus)
        self.world.register_component(StatusDuration)
