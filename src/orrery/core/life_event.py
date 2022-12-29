from __future__ import annotations

import random
from abc import abstractmethod
from typing import Dict, List, Optional, Protocol, Union

from orrery.core.ecs import GameObject, World
from orrery.core.event import Event, EventLog, RoleBinder, RoleList
from orrery.core.time import SimDateTime


class ILifeEvent(Protocol):
    """Interface for classes that create life events"""

    @abstractmethod
    def get_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def instantiate(
        self, world: World, *args: GameObject, **kwargs: GameObject
    ) -> Optional[LifeEventInstance]:
        """Attempts to create a new Event instance"""
        raise NotImplementedError

    @abstractmethod
    def try_execute_event(
        self, world: World, *args: GameObject, **kwargs: GameObject
    ) -> bool:
        """Attempts to instantiate and execute the event"""
        raise NotImplementedError


class LifeEventInstance:
    """
    An instance of a life event with GameObjects bound to roles

    Attributes
    ----------
    name: str
        Name of the LifeEventType and the LifeEvent it instantiates
    roles: RoleList
        The roles that need to be cast for this event to be executed
    effect: LifeEventEffectFn
        Function that executes changes to the world state base don the event
    """

    __slots__ = "name", "roles", "effect"

    def __init__(
        self,
        name: str,
        roles: RoleList,
        effect: Optional[LifeEventEffectFn],
    ) -> None:
        self.name: str = name
        self.roles: RoleList = roles
        self.effect: Optional[LifeEventEffectFn] = effect

    def execute(self, world: World) -> None:
        """Executes the LifeEvent instance, emitting an event"""
        event = Event(
            name=self.name,
            timestamp=world.get_resource(SimDateTime).to_iso_str(),
            roles=[r for r in self.roles],
        )

        world.get_resource(EventLog).record_event(event)

        if self.effect is not None:
            self.effect(world, event)


class LifeEvent:
    """
    User-facing class for implementing behaviors around life events

    This is adapted from:
    https://github.com/ianhorswill/CitySimulator/blob/master/Assets/Codes/Action/Actions/ActionType.cs

    Attributes
    ----------
    name: str
        Name of the LifeEventType and the LifeEvent it instantiates
    bind_fn: orrery.core.event.RoleBinder
        Function that attempt to bind roles for the LifeEvent
    probability: LifeEventProbabilityFn
        The relative frequency of this event compared to other events
    effect: LifeEventEffectFn
        Function that executes changes to the world state base don the event
    """

    __slots__ = "name", "probability", "bind_fn", "effect"

    def __init__(
        self,
        name: str,
        bind_fn: RoleBinder,
        probability: Union[LifeEventProbabilityFn, float],
        effect: Optional[LifeEventEffectFn] = None,
    ) -> None:
        self.name: str = name
        self.bind_fn: RoleBinder = bind_fn
        self.probability: LifeEventProbabilityFn = (
            probability if callable(probability) else (lambda world, event: probability)
        )
        self.effect: Optional[LifeEventEffectFn] = effect

    def get_name(self) -> str:
        return self.name

    def instantiate(
        self, world: World, *args: GameObject, **kwargs: GameObject
    ) -> Optional[LifeEventInstance]:
        """
        Attempts to create a new LifeEvent instance

        Parameters
        ----------
        world: World
            Neighborly world instance
        *args: GameObject
            Positional GameObject bindings to Roles
        **kwargs: GameObject
            Keyword bindings of GameObjects to Roles
        """
        if roles := self.bind_fn(world, *args, **kwargs):
            return LifeEventInstance(self.name, roles, self.effect)
        return None

    def try_execute_event(
        self, world: World, *args: GameObject, **kwargs: GameObject
    ) -> bool:
        """
        Attempt to instantiate and execute this LifeEventType

        Parameters
        ----------
        world: World
            Neighborly world instance
        *args: GameObject
            Positional GameObject bindings to Roles
        **kwargs: GameObject
            Keyword bindings of GameObjects to Roles

        Returns
        -------
        bool
            Returns True if the event is instantiated successfully and executed
        """
        event = self.instantiate(world, *args, **kwargs)
        rng = world.get_resource(random.Random)
        if event is not None and rng.random() < self.probability(world, event):
            event.execute(world)
            return True
        return False


class LifeEventEffectFn(Protocol):
    """Callback function called when an event is executed"""

    def __call__(self, world: World, event: Event) -> None:
        raise NotImplementedError


class LifeEventProbabilityFn(Protocol):
    """Function called to determine the probability of an event executing"""

    def __call__(self, world: World, event: LifeEventInstance) -> float:
        raise NotImplementedError


class LifeEventLibrary:
    """
    Static class used to store instances of LifeEventTypes for
    use at runtime.
    """

    _registry: Dict[str, ILifeEvent] = {}

    @classmethod
    def add(cls, life_event: ILifeEvent, name: Optional[str] = None) -> None:
        """Register a new LifeEventType mapped to a name"""
        key_name = name if name else life_event.get_name()
        cls._registry[key_name] = life_event

    @classmethod
    def get_all(cls) -> List[ILifeEvent]:
        """Get all LifeEventTypes stores in the Library"""
        return list(cls._registry.values())

    @classmethod
    def get(cls, name: str) -> ILifeEvent:
        """Get a LifeEventType using a name"""
        return cls._registry[name]
