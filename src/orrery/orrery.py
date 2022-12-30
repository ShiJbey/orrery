from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple

from orrery import event_callbacks
from orrery.components.business import (
    Business,
    BusinessFactory,
    BusinessLibrary,
    ClosedForBusiness,
    InTheWorkforce,
    Occupation,
    OccupationTypeLibrary,
    OpenForBusiness,
    Services,
    ServicesFactory,
    Unemployed,
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
from orrery.components.shared import (
    Active,
    Building,
    FrequentedLocations,
    Location,
    Name,
    Position2D,
)
from orrery.constants import (
    BUSINESS_UPDATE_PHASE,
    CHARACTER_UPDATE_PHASE,
    CORE_SYSTEMS_PHASE,
    SETTLEMENT_UPDATE_PHASE,
)
from orrery.core.activity import (
    ActivityLibrary,
    ActivityManager,
    ActivityManagerFactory,
    ActivityToVirtueMap,
)
from orrery.core.config import OrreryConfig
from orrery.core.ecs import World
from orrery.core.event import EventLog
from orrery.core.life_event import LifeEventLibrary
from orrery.core.relationship import RelationshipManager, UpdateRelationshipsSystem
from orrery.core.social_rule import SocialRuleLibrary
from orrery.core.status import RelationshipStatus, Status, StatusManager
from orrery.core.time import SimDateTime, TimeDelta
from orrery.core.tracery import Tracery
from orrery.core.traits import TraitManager
from orrery.core.virtues import VirtueVector, VirtueVectorFactory
from orrery.systems import (
    BuildBusinessSystem,
    BuildHousingSystem,
    BusinessUpdateSystem,
    CharacterAgingSystem,
    EventSystem,
    FindEmployeesSystem,
    LifeEventSystem,
    MeetNewPeopleSystem,
    PregnantStatusSystem,
    SpawnResidentSystem,
    StatusDurationSystem,
    TimeSystem,
    UnemployedStatusSystem,
)


class PluginSetupError(Exception):
    """
    Exception thrown when an error occurs while loading a plugin

    Attributes
    ----------
    message: str
        Text explaining the error that occurred
    """

    __slots__ = "message"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message: str = message

    def __str__(self) -> str:
        return self.message

    def __repr__(self) -> str:
        return f"PluginSetupError('{self.message}')"


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
    """
    Main entry class for running Orrery simulations.

    Attributes
    ----------
    world: World
        Entity-component system (ECS) that manages entities and procedures in the virtual world
    config: OrreryConfig
        Configuration settings for the simulation
    plugins: List[Tuple[Plugin, Dict[str, Any]]]
        List of loaded plugins and their configuration data
    """

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
        self.world.add_resource(OccupationTypeLibrary())
        self.world.add_resource(LifeEventLibrary())

        # Add default systems
        self.world.add_system(StatusDurationSystem(), CHARACTER_UPDATE_PHASE)
        self.world.add_system(PregnantStatusSystem(), CHARACTER_UPDATE_PHASE)
        self.world.add_system(UnemployedStatusSystem(), CHARACTER_UPDATE_PHASE)
        self.world.add_system(UpdateRelationshipsSystem(), CHARACTER_UPDATE_PHASE)
        self.world.add_system(MeetNewPeopleSystem(), CHARACTER_UPDATE_PHASE)
        self.world.add_system(LifeEventSystem(), CORE_SYSTEMS_PHASE)
        self.world.add_system(EventSystem(), CORE_SYSTEMS_PHASE)
        self.world.add_system(TimeSystem(), CORE_SYSTEMS_PHASE)
        self.world.add_system(CharacterAgingSystem(), CHARACTER_UPDATE_PHASE)
        self.world.add_system(BusinessUpdateSystem(), BUSINESS_UPDATE_PHASE)
        self.world.add_system(FindEmployeesSystem(), BUSINESS_UPDATE_PHASE)
        self.world.add_system(BuildHousingSystem(), SETTLEMENT_UPDATE_PHASE)
        self.world.add_system(SpawnResidentSystem(), SETTLEMENT_UPDATE_PHASE)
        self.world.add_system(BuildBusinessSystem(), SETTLEMENT_UPDATE_PHASE)

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
        self.world.register_component(StatusManager)
        self.world.register_component(FrequentedLocations)
        self.world.register_component(Status)
        self.world.register_component(RelationshipStatus)
        self.world.register_component(Unemployed)

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
        """
        Add plugin to simulation

        Parameters
        ---------
        plugin: Plugin
            The plugin instance to load
        **kwargs: Any
            Keyword arguments to pass to the plugin's 'setup()' function
        """
        self.plugins.append((plugin, {**kwargs}))
        plugin.setup(self.world, **kwargs)

    def run_for(self, years: int) -> None:
        """
        Run the simulation for a given number of simulated years

        Parameters
        ----------
        years: int
            Simulated years to run the simulation for
        """
        stop_date = self.world.get_resource(SimDateTime).copy() + TimeDelta(years=years)
        self.run_until(stop_date)

    def run_until(self, stop_date: SimDateTime) -> None:
        """
        Run the simulation until a specific date is reached

        Parameters
        ----------
        stop_date: SimDateTime
            The date to stop stepping the simulation
        """
        try:
            current_date = self.world.get_resource(SimDateTime)
            while stop_date >= current_date:
                self.step()
        except KeyboardInterrupt:
            print("\nStopping Simulation")

    def step(self) -> None:
        """Advance the simulation a single timestep"""
        self.world.step()
