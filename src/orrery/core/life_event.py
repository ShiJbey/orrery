from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

from orrery.core.ecs import GameObject, World
from orrery.core.event import Event
from orrery.core.roles import Role, RoleList
from orrery.core.time import SimDateTime


class LifeEvent(Event, ABC):
    """
    User-facing class for implementing behaviors around life events

    This is adapted from:
    https://github.com/ianhorswill/CitySimulator/blob/master/Assets/Codes/Action/Actions/ActionType.cs
    """

    __slots__ = "_roles"

    def __init__(
        self,
        timestamp: SimDateTime,
        roles: Iterable[Role],
    ) -> None:
        """
        Parameters
        ----------
        timestamp: SimDateTime
            Timestamp for when this event
        roles: Dict[str, GameObject
            The names of roles mapped to GameObjects
        """
        super().__init__(timestamp)
        self._roles: RoleList = RoleList(roles)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this LifeEvent to a dictionary"""
        return {
            **super().to_dict(),
            "roles": {role.name: role.gameobject for role in self._roles},
        }

    def iter_roles(self) -> Iterator[Role]:
        return self._roles.__iter__()

    def __getitem__(self, role_name: str) -> GameObject:
        return self._roles[role_name]

    def __repr__(self) -> str:
        return "{}(timestamp={}, roles=[{}])".format(
            self.get_type(), str(self.get_timestamp()), self._roles
        )

    def __str__(self) -> str:
        return "{} [@ {}] {}".format(
            self.get_type(),
            str(self.get_timestamp()),
            ", ".join([str(role) for role in self._roles]),
        )


class ActionableLifeEvent(LifeEvent):
    """
    User-facing class for implementing behaviors around life events

    This is adapted from:
    https://github.com/ianhorswill/CitySimulator/blob/master/Assets/Codes/Action/Actions/ActionType.cs
    """

    optional: bool = False
    initiator: str = ""
    requires_confirmation: Optional[Tuple[str, ...]] = None
    base_priority: int = 1

    __slots__ = "_roles"

    def __init__(
        self,
        timestamp: SimDateTime,
        roles: Iterable[Role],
    ) -> None:
        """
        Parameters
        ----------
        timestamp: SimDateTime
            Timestamp for when this event
        roles: Dict[str, GameObject
            The names of roles mapped to GameObjects
        """
        super().__init__(timestamp, roles)

    def get_priority(self) -> float:
        """Get the probability of an instance of this event happening

        Returns
        -------
        float
            The probability of the event given the GameObjects bound
            to the roles in the LifeEventInstance
        """
        return self.base_priority

    @abstractmethod
    def execute(self) -> None:
        """Executes the LifeEvent instance, emitting an event"""
        raise NotImplementedError

    def is_valid(self, world: World) -> bool:
        """Check that all gameobjects still meet the preconditions for their roles"""
        return self.instantiate(world, bindings=self._roles) is not None

    def get_initiator(self) -> GameObject:
        return self._roles[self.initiator]

    @classmethod
    @abstractmethod
    def instantiate(
        cls,
        world: World,
        bindings: Optional[RoleList] = None,
    ) -> Optional[ActionableLifeEvent]:
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


class LifeEventBuffer:
    """Manages all the events that have occurred in the simulation during a timestep"""

    __slots__ = ("_event_buffer",)

    def __init__(self) -> None:
        self._event_buffer: List[LifeEvent] = []

    def iter_events(self) -> Iterator[LifeEvent]:
        """Return an iterator to all the events in the buffer regardless of type"""
        return self._event_buffer.__iter__()

    def append(self, event: LifeEvent) -> None:
        """Add a new event to the buffer

        Parameters
        ----------
        event: Event
            An event instance
        """
        self._event_buffer.append(event)

    def clear(self) -> None:
        """Clears all events from the buffer"""
        self._event_buffer.clear()
