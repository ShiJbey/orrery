from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import Any, Dict, Iterator, List, Optional, final

from orrery import Component, Query
from orrery.core.ecs import GameObject, World
from orrery.core.event import Event, EventHandler, RoleInstance, RoleList
from orrery.core.time import SimDateTime


class ILifeEvent(ABC):
    """Interface for classes that create life events"""

    @abstractmethod
    def get_name(self) -> str:
        """Get the name of the event"""
        raise NotImplementedError

    @abstractmethod
    def get_initiator_role(self) -> str:
        """Return the name of the role that initiates the life event"""
        raise NotImplementedError

    @abstractmethod
    def get_priority(self, event: LifeEventInstance) -> float:
        """Get the probability of an instance of this event happening

        Parameters
        ----------
        event: LifeEventInstance
            An instance of a life event containing bound roles

        Returns
        -------
        float
            The probability of the event given the GameObjects bound
            to the roles in the LifeEventInstance
        """
        raise NotImplementedError

    @abstractmethod
    def instantiate(
        self, world: World, bindings: Optional[Dict[str, GameObject]] = None
    ) -> Optional[LifeEventInstance]:
        """Attempts to create a new LifeEvent instance

        Parameters
        ----------
        world: World
            Neighborly world instance
        bindings: Dict[str, GameObject], optional
            Suggested bindings of role names mapped to GameObjects

        Returns
        -------
        Optional[LifeEventInstance]
            An instance of this life event if all roles are bound successfully
        """
        raise NotImplementedError

    @abstractmethod
    def execute(self, event: LifeEventInstance) -> None:
        """Update the world state using the event data"""
        raise NotImplementedError


@final
class LifeEventInstance:
    """
    An instance of a life event with GameObjects bound to roles

    Attributes
    ----------
    roles: RoleList
        The roles that need to be cast for this event to be executed
    event_type: ILifeEvent
        The LifeEvent that spawned this instance
    """

    __slots__ = "event_type", "roles", "world"

    def __init__(
        self,
        event_type: ILifeEvent,
        roles: Dict[str, GameObject],
        world: World,
    ) -> None:
        self.event_type: ILifeEvent = event_type
        self.roles: Dict[str, GameObject] = roles
        self.world: World = world

    def __getitem__(self, role_name: str) -> GameObject:
        return self.roles[role_name]

    def get_name(self) -> str:
        """Return the name of this life event instance"""
        return self.event_type.get_name()

    def get_priority(self) -> float:
        """Return the priority of this life event instance"""
        return self.event_type.get_priority(self)

    def is_valid(self) -> bool:
        """Check that all gameobjects still meet the preconditions for their roles"""
        return (
            self.event_type.instantiate(self.world, bindings={**self.roles}) is not None
        )

    def execute(self) -> None:
        """Executes the LifeEvent instance, emitting an event"""
        self.event_type.execute(self)

        event = Event(
            name=self.get_name(),
            timestamp=self.world.get_resource(SimDateTime).to_iso_str(),
            roles=[RoleInstance(r, g.uid) for r, g in self.roles.items()],
        )

        self.world.get_resource(EventHandler).emit(event)


class LifeEvent(ILifeEvent, ABC):
    """
    User-facing class for implementing behaviors around life events

    This is adapted from:
    https://github.com/ianhorswill/CitySimulator/blob/master/Assets/Codes/Action/Actions/ActionType.cs
    """

    __slots__ = "_name", "_initiator_role", "_role_query"

    def __init__(
        self,
        name: str,
        initiator_role: str,
        role_query: Query,
    ) -> None:
        """
        Parameters
        ----------
        name: str
            The name of the event
        initiator_role: str
            The name of the role a character is automatically cast into when attempting
            to instantiate this life event
        role_query: Query
            A query defining requirements for roles and with all the roles as output
            variables
        """
        self._name: str = name
        self._initiator_role: str = initiator_role
        self._role_query: Query = role_query

    def get_initiator_role(self) -> str:
        """Return the name of the role that initiates this life event"""
        return self._initiator_role

    @final
    def get_name(self) -> str:
        """Get the name of this life event"""
        return self._name

    @final
    def instantiate(
        self, world: World, bindings: Optional[Dict[str, GameObject]] = None
    ) -> Optional[LifeEventInstance]:
        """Attempts to create a new LifeEvent instance

        Parameters
        ----------
        world: World
            Neighborly world instance
        bindings: Dict[str, GameObject], optional
            Suggested bindings of role names mapped to GameObjects

        Returns
        -------
        Optional[LifeEventInstance]
            An instance of this life event if all roles are bound successfully
        """
        if results := self._role_query.execute(world, bindings):
            chosen_result = world.get_resource(random.Random).choice(results)
            chosen_objects = [world.get_gameobject(uid) for uid in chosen_result]
            roles = dict(zip(self._role_query.get_symbols(), chosen_objects))
            return LifeEventInstance(self, roles, world)
        return None


class LifeEventQueue(Component):
    """Contains a  queue of life event instances"""

    __slots__ = "_events"

    def __init__(self) -> None:
        super().__init__()
        self._events: List[LifeEventInstance] = []

    def push(self, event: LifeEventInstance) -> None:
        self._events.append(event)

    def pop(self, event: LifeEventInstance) -> None:
        self._events.pop(0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "events": [
                {"name": e.get_name(), "roles": {r: g.uid for r, g in e.roles.items()}}
                for e in self._events
            ]
        }

    def clear(self) -> None:
        self._events.clear()

    def __len__(self) -> int:
        return len(self._events)

    def __iter__(self) -> Iterator:
        return self._events.__iter__()


class LifeEventConfig(dict[str, Any]):
    """Shared dictionary of configuration settings for all life events"""

    pass
