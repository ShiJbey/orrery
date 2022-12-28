from __future__ import annotations
from abc import ABC, abstractmethod

import random
from typing import Any, List, Dict, Tuple

from orrery.core.activity import (
    ActivityLibrary,
    ActivityManager,
    ActivityManagerFactory,
)
from orrery.components.business import (
    Business,
    BusinessFactory,
    BusinessLibrary,
    ClosedForBusiness,
    InTheWorkforce,
    Occupation,
    OpenForBusiness,
    Services,
    ServicesFactory,
    WorkHistory,
)
from orrery.components.character import (
    CanAge,
    CanDie,
    CanGetPregnant,
    CharacterLibrary,
    CollegeGraduate,
    Deceased,
    Departed,
    GameCharacter,
    GameCharacterFactory,
    Retired,
)
from orrery.components.residence import Residence, ResidenceLibrary, Resident, Vacant
from orrery.components.shared import Active, Building, Location, Name, Position2D
from orrery.core.config import ActivityToVirtueMap, OrreryConfig
from orrery.core.ecs import World
from orrery.core.event import EventLog
from orrery.core.relationship import RelationshipManager, UpdateRelationshipsSystem
from orrery.core.social_rule import SocialRuleLibrary
from orrery.core.status import RelationshipStatus, StatusDuration, statusDurationSystem
from orrery.systems import (
    BuildBusinessSystem,
    BuildHousingSystem,
    BusinessUpdateSystem,
    CharacterAgingSystem,
    EventSystem,
    FindEmployeesSystem,
    MeetNewPeopleSystem,
    SpawnResidentSystem,
    TimeSystem,
)
from orrery.core.time import SimDateTime
from orrery.core.tracery import Tracery
from orrery.core.traits import TraitManager
from orrery.core.virtues import VirtueVector, VirtueVectorFactory
from orrery import event_callbacks


class PluginSetupError(Exception):
    """Exception thrown when an error occurs while loading a plugin"""

    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class Plugin(ABC):
    """
    Plugins are loaded before the simulation runs and can modify
    a Simulation's World instance to add new components, systems,
    resources, and entity archetypes.
    """

    @classmethod
    def get_name(cls) -> str:
        """Return the name of this plugin"""
        return cls.__name__

    @abstractmethod
    def setup(self, world: World, **kwargs: Any) -> None:
        """Add the plugin data to the simulation"""
        raise NotImplementedError


class Orrery:

    __slots__ = "world", "config", "plugins"

    def __init__(self, config: OrreryConfig) -> None:
        self.world: World = World()
        self.config: OrreryConfig = config
        self.plugins: List[Tuple[Plugin, Dict[str, Any]]] = []

        # Add default resources
        self.world.add_resource(config)
        self.world.add_resource(Tracery())
        self.world.add_resource(random.Random(config.seed))
        self.world.add_resource(SocialRuleLibrary())
        self.world.add_resource(CharacterLibrary())
        self.world.add_resource(BusinessLibrary())
        self.world.add_resource(ResidenceLibrary())
        self.world.add_resource(ActivityLibrary())
        self.world.add_resource(ActivityToVirtueMap())
        self.world.add_resource(SimDateTime())
        self.world.add_resource(EventLog())

        # Add default systems
        self.world.add_system(statusDurationSystem())
        self.world.add_system(UpdateRelationshipsSystem())
        self.world.add_system(MeetNewPeopleSystem())
        self.world.add_system(EventSystem())
        self.world.add_system(TimeSystem())
        self.world.add_system(CharacterAgingSystem())
        self.world.add_system(BusinessUpdateSystem())
        self.world.add_system(FindEmployeesSystem())
        self.world.add_system(BuildHousingSystem())
        self.world.add_system(SpawnResidentSystem())
        self.world.add_system(BuildBusinessSystem())

        # Register components
        self.world.register_component(Active)
        self.world.register_component(GameCharacter, factory=GameCharacterFactory())
        self.world.register_component(Name)
        self.world.register_component(RelationshipManager)
        self.world.register_component(TraitManager)
        self.world.register_component(Location)
        self.world.register_component(VirtueVector, factory=VirtueVectorFactory())
        self.world.register_component(ActivityManager, factory=ActivityManagerFactory())
        self.world.register_component(RelationshipStatus)
        self.world.register_component(StatusDuration)
        self.world.register_component(Occupation)
        self.world.register_component(WorkHistory)
        self.world.register_component(Services, factory=ServicesFactory())
        self.world.register_component(ClosedForBusiness)
        self.world.register_component(OpenForBusiness)
        self.world.register_component(Business, factory=BusinessFactory())
        self.world.register_component(InTheWorkforce)
        self.world.register_component(Departed)
        self.world.register_component(CanAge)
        self.world.register_component(CanDie)
        self.world.register_component(CanGetPregnant)
        self.world.register_component(Deceased)
        self.world.register_component(Retired)
        self.world.register_component(CollegeGraduate)
        self.world.register_component(Residence)
        self.world.register_component(Resident)
        self.world.register_component(Vacant)
        self.world.register_component(Building)
        self.world.register_component(Position2D)

        # Configure printing every event to the console
        if config.verbose:
            self.world.get_resource(EventLog).subscribe(lambda e: print(str(e)))

        # Configure event callback functions
        self.world.get_resource(EventLog).on(
            "Depart", event_callbacks.on_depart_callback
        )

        self.world.get_resource(EventLog).on(
            "Retire", event_callbacks.remove_retired_from_occupation
        )

        self.world.get_resource(EventLog).on(
            "Retire", event_callbacks.remove_retired_from_occupation
        )

        self.world.get_resource(EventLog).on(
            "Death", event_callbacks.remove_deceased_from_occupation
        )

        self.world.get_resource(EventLog).on(
            "Death", event_callbacks.remove_deceased_from_residence
        )

        self.world.get_resource(EventLog).on(
            "Depart", event_callbacks.remove_departed_from_residence
        )

        self.world.get_resource(EventLog).on(
            "Depart", event_callbacks.remove_departed_from_occupation
        )

        self.world.get_resource(EventLog).on(
            "Death", event_callbacks.remove_statuses_from_deceased
        )

        self.world.get_resource(EventLog).on(
            "Depart", event_callbacks.remove_statuses_from_departed
        )

    def load_plugin(self, plugin: Plugin, **kwargs: Any) -> None:
        """Add plugin to simulation"""
        self.plugins.append((plugin, {**kwargs}))
        plugin.setup(self.world, **kwargs)
