from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar

from orrery.components.activity import Activities, LikedActivities
from orrery.components.business import (
    Business,
    ClosedForBusiness,
    InTheWorkforce,
    Occupation,
    OpenForBusiness,
    Services,
    WorkHistory,
)
from orrery.components.character import (
    CanAge,
    CanDie,
    CanGetPregnant,
    CollegeGraduate,
    Deceased,
    Departed,
    GameCharacter,
    Retired,
)
from orrery.components.relationship import RelationshipManager
from orrery.components.residence import Residence, Resident, Vacant
from orrery.components.settlement import Settlement
from orrery.components.shared import (
    Active,
    Building,
    FrequentedLocations,
    Location,
    Name,
    Position2D,
)
from orrery.components.virtues import Virtues
from orrery.config import OrreryConfig
from orrery.content_management import (
    ActivityLibrary,
    ActivityToVirtueMap,
    BusinessLibrary,
    CharacterLibrary,
    LifeEventLibrary,
    OccupationTypeLibrary,
    ResidenceLibrary,
    ServiceLibrary,
    SocialRuleLibrary,
)
from orrery.core.ai import AIComponent
from orrery.core.ecs import Component, IComponentFactory, ISystem, World
from orrery.core.event import EventHandler
from orrery.core.status import StatusManager
from orrery.core.time import SimDateTime, TimeDelta
from orrery.core.tracery import Tracery
from orrery.core.traits import TraitManager
from orrery.factories.activity import ActivitiesFactory, LikedActivitiesFactory
from orrery.factories.business import BusinessFactory, ServicesFactory
from orrery.factories.character import GameCharacterFactory
from orrery.factories.shared import FrequentedLocationsFactory, LocationFactory
from orrery.factories.virtues import VirtuesFactory
from orrery.systems import (
    AIActionSystem,
    BuildBusinessSystem,
    BuildHousingSystem,
    BusinessUpdateSystem,
    CharacterAgingSystem,
    CharacterUpdateSystemGroup,
    CleanUpSystemGroup,
    CoreSystemsSystemGroup,
    DatingStatusSystem,
    EarlyCharacterUpdateSystemGroup,
    EventListenersSystemGroup,
    EventSystem,
    FindEmployeesSystem,
    InitializationSystemGroup,
    LateCharacterUpdateSystemGroup,
    LifeEventSystem,
    MarkUnemployedNewCharactersSystem,
    MarriedStatusSystem,
    MeetNewPeopleSystem,
    OccupationUpdateSystem,
    OnBecomeYoungAdultSystem,
    OnDeathSystem,
    OnDepartSystem,
    OnJoinSettlementSystem,
    PregnantStatusSystem,
    PrintEventBufferSystem,
    ReevaluateSocialRulesSystem,
    RelationshipUpdateSystem,
    RelationshipUpdateSystemGroup,
    RemoveFrequentedFromDepartedSystem,
    RemoveRetiredFromOccupationSystem,
    SpawnResidentSystem,
    StatusUpdateSystemGroup,
    TimeSystem,
    UnemployedStatusSystem,
    UpdateFrequentedLocationSystem,
)

_CT = TypeVar("_CT", bound=Component)
_RT = TypeVar("_RT", bound=Any)
_ST = TypeVar("_ST", bound=ISystem)


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

    def __init__(self, config: Optional[OrreryConfig] = None) -> None:
        self.world: World = World()
        self.config: OrreryConfig = config if config else OrreryConfig()
        self.plugins: List[Tuple[Plugin, Dict[str, Any]]] = []

        # Seed RNG for libraries we don't control, like Tracery
        random.seed(self.config.seed)

        # Add default resources
        self.world.add_resource(self.config)
        self.world.add_resource(random.Random(self.config.seed))
        self.world.add_resource(Tracery())
        self.world.add_resource(SocialRuleLibrary())
        self.world.add_resource(CharacterLibrary())
        self.world.add_resource(BusinessLibrary())
        self.world.add_resource(ResidenceLibrary())
        self.world.add_resource(ActivityLibrary())
        self.world.add_resource(ActivityToVirtueMap())
        self.world.add_resource(SimDateTime())
        self.world.add_resource(EventHandler())
        self.world.add_resource(OccupationTypeLibrary())
        self.world.add_resource(LifeEventLibrary())
        self.world.add_resource(ServiceLibrary())

        # Add default system groups
        self.world.add_system(InitializationSystemGroup())
        self.world.add_system(StatusUpdateSystemGroup())
        self.world.add_system(BusinessUpdateSystem())
        self.world.add_system(CharacterUpdateSystemGroup())
        self.world.add_system(EarlyCharacterUpdateSystemGroup())
        self.world.add_system(LateCharacterUpdateSystemGroup())
        self.world.add_system(RelationshipUpdateSystemGroup())
        self.world.add_system(CoreSystemsSystemGroup())
        self.world.add_system(EventListenersSystemGroup())
        self.world.add_system(CleanUpSystemGroup())

        # Add default systems
        self.world.add_system(RelationshipUpdateSystem())
        self.world.add_system(MeetNewPeopleSystem())
        self.world.add_system(LifeEventSystem())
        self.world.add_system(EventSystem())
        self.world.add_system(TimeSystem())
        self.world.add_system(CharacterAgingSystem())
        self.world.add_system(DatingStatusSystem())
        self.world.add_system(MarriedStatusSystem())
        self.world.add_system(PregnantStatusSystem())
        self.world.add_system(UnemployedStatusSystem())
        self.world.add_system(OccupationUpdateSystem())
        self.world.add_system(BusinessUpdateSystem())
        self.world.add_system(FindEmployeesSystem())
        self.world.add_system(BuildHousingSystem())
        self.world.add_system(SpawnResidentSystem())
        self.world.add_system(BuildBusinessSystem())
        self.world.add_system(ReevaluateSocialRulesSystem())
        self.world.add_system(UpdateFrequentedLocationSystem())
        self.world.add_system(MarkUnemployedNewCharactersSystem())
        self.world.add_system(RemoveFrequentedFromDepartedSystem())
        self.world.add_system(AIActionSystem())
        self.world.add_system(OnDepartSystem())
        self.world.add_system(OnDeathSystem())
        self.world.add_system(OnJoinSettlementSystem())
        self.world.add_system(RemoveRetiredFromOccupationSystem())
        self.world.add_system(OnBecomeYoungAdultSystem())

        # Register components
        self.world.register_component(Active)
        self.world.register_component(AIComponent)
        self.world.register_component(GameCharacter, factory=GameCharacterFactory())
        self.world.register_component(Name)
        self.world.register_component(RelationshipManager)
        self.world.register_component(TraitManager)
        self.world.register_component(Location, factory=LocationFactory())
        self.world.register_component(Virtues, factory=VirtuesFactory())
        self.world.register_component(Activities, factory=ActivitiesFactory())
        self.world.register_component(LikedActivities, factory=LikedActivitiesFactory())
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
        self.world.register_component(StatusManager)
        self.world.register_component(
            FrequentedLocations, factory=FrequentedLocationsFactory()
        )
        self.world.register_component(Settlement)

        # Configure printing every event to the console
        if self.config.verbose:
            self.world.add_system(PrintEventBufferSystem())

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

    def register_component(
        self,
        component_type: Type[Component],
        name: Optional[str] = None,
        factory: Optional[IComponentFactory] = None,
    ) -> None:
        """Register a component type with the  simulation

        Registers a component class type with the simulation's World instance.
        This allows content authors to use the Component in YAML files and
        EntityPrefabs.

        Parameters
        ----------
        component_type: Type[Component]
            The type of component to add
        name: str, optional
            A name to register the component type under (defaults to name of class)
        factory: IComponentFactory, optional
            A factory instance used to construct this component type
            (defaults to DefaultComponentFactory())
        """

        self.world.register_component(component_type, name, factory)

    def add_resource(self, resource: Any) -> None:
        """Add a shared resource

        Parameters
        ----------
        resource: Any
            An instance of the resource to add to the class
        """

        self.world.add_resource(resource)

    def add_system(self, system: ISystem, priority: int = 0) -> None:
        """Add a simulation system

        Parameters
        ----------
        system: ISystem
            The system to add
        priority: int
            The priority of this system.
            The higher the number the sooner it runs at the beginning of a simulation step
        """

        self.world.add_system(system, priority=priority)

    def component(
        self,
        name: Optional[str] = None,
        factory: Optional[IComponentFactory] = None,
    ):
        """Register a component type with the  simulation

        Registers a component class type with the simulation's World instance.
        This allows content authors to use the Component in YAML files and
        EntityPrefabs.

        Parameters
        ----------
        name: str, optional
            A name to register the component type under (defaults to name of class)
        factory: IComponentFactory, optional
            A factory instance used to construct this component type
            (defaults to DefaultComponentFactory())
        """

        def decorator(cls: Type[_CT]) -> Type[_CT]:
            self.world.register_component(cls, name, factory)
            return cls

        return decorator

    def resource(self, **kwargs: Any):
        """Add a class as a shared resource

        This decorator adds an instance of the decorated class as a shared resource.

        Parameters
        ----------
        **kwargs: Any
            Keyword arguments to pass to the constructor of the decorated class
        """

        def decorator(cls: Type[_RT]) -> Type[_RT]:
            self.world.add_resource(cls(**kwargs))
            return cls

        return decorator

    def system(self, priority: int = 0, **kwargs: Any):
        """Add a class as a simulation system

        This decorator adds an instance of the decorated class as a shared resource.

        Parameters
        ----------
        priority: int
            The priority of this system.
            The higher the number the sooner it runs at the beginning of a simulation step
        **kwargs: Any
            Keyword arguments to pass to the constructor of the decorated class
        """

        def decorator(cls: Type[_ST]) -> Type[_ST]:
            self.world.add_system(cls(**kwargs), priority=priority)
            return cls

        return decorator
