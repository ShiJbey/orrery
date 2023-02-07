from __future__ import annotations

from collections import defaultdict
from typing import (
    Any,
    ClassVar,
    DefaultDict,
    Dict,
    Iterator,
    List,
    Optional,
    Protocol,
    Type,
    TypeVar,
)

from orrery.core.ecs import GameObject, World
from orrery.core.serializable import ISerializable


class RoleList:
    """A collection of roles for an event"""

    __slots__ = "_roles", "_sorted_roles"

    def __init__(self, roles: Optional[List[RoleInstance]] = None) -> None:
        self._roles: List[RoleInstance] = []
        self._sorted_roles: Dict[str, List[RoleInstance]] = {}

        if roles:
            for role in roles:
                self.add_role(role)

    @property
    def roles(self) -> List[RoleInstance]:
        return self._roles

    def add_role(self, role: RoleInstance) -> None:
        """Add role to the event"""
        self._roles.append(role)
        if role.name not in self._sorted_roles:
            self._sorted_roles[role.name] = []
        self._sorted_roles[role.name].append(role)

    def get_all(self, role_name: str) -> List[int]:
        """Return the IDs of all GameObjects bound to the given role name"""
        return list(map(lambda role: role.gid, self._sorted_roles[role_name]))

    def __getitem__(self, role_name: str) -> int:
        return self._sorted_roles[role_name][0].gid

    def __iter__(self):
        return self._roles.__iter__()


class Event:
    """
    LifeEvents contain information about occurrences that
    happened in the story world.

    Attributes
    ----------
    name: str
        Name of the event
    timestamp: str
        Timestamp for when the event occurred
    roles: RoleList
        GameObjects involved with this event
    """

    __slots__ = "timestamp", "name", "roles", "uid"

    _next_event_id: ClassVar[int] = 0

    def __init__(self, name: str, timestamp: str, roles: List[RoleInstance]) -> None:
        self.uid: int = Event._next_event_id
        Event._next_event_id += 1
        self.name: str = name
        self.timestamp: str = timestamp
        self.roles: RoleList = RoleList(roles)

    def add_role(self, role: RoleInstance) -> None:
        """Add role to the event"""
        self.roles.add_role(role)

    def get_type(self) -> str:
        """Return the type of this event"""
        return self.name

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this LifeEvent to a dictionary"""
        return {
            "name": self.name,
            "timestamp": self.timestamp,
            "roles": [role.to_dict() for role in self.roles],
        }

    def get_all(self, role_name: str) -> List[int]:
        """Return the IDs of all GameObjects bound to the given role name"""
        return self.roles.get_all(role_name)

    def __getitem__(self, role_name: str) -> int:
        return self.roles[role_name]

    def __le__(self, other: Event) -> bool:
        return self.uid <= other.uid

    def __lt__(self, other: Event) -> bool:
        return self.uid < other.uid

    def __ge__(self, other: Event) -> bool:
        return self.uid >= other.uid

    def __gt__(self, other: Event) -> bool:
        return self.uid > other.uid

    def __repr__(self) -> str:
        return "LifeEvent(name={}, timestamp={}, roles=[{}])".format(
            self.name, self.timestamp, self.roles
        )

    def __str__(self) -> str:
        return f"{self.name} [at {self.timestamp}] : {', '.join(map(lambda r: f'{r.name}:{r.gid}', self.roles))}"


class RoleInstance:
    """A role name bound to a GameObject ID"""

    __slots__ = "_name", "_gid"

    def __init__(self, name: str, gid: int) -> None:
        self._name: str = name
        self._gid: int = gid

    @property
    def name(self):
        """Get the name of the role"""
        return self._name

    @property
    def gid(self):
        """Get the ID of the GameObject bound to the role"""
        return self._gid

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "gid": self.gid}

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, gid={self.gid})"


_ET = TypeVar("_ET", bound=Event)


class EventHandler(ISerializable):
    """
    Global resource that manages all the LifeEvents that have occurred in the simulation.

    This resource should always be present in the simulation.
    """

    __slots__ = (
        "_event_history",
        "_per_gameobject",
        "_event_buffers_by_type",
        "_event_buffer",
    )

    def __init__(self) -> None:
        self._event_history: List[Event] = []
        self._per_gameobject: DefaultDict[int, List[Event]] = defaultdict(list)
        self._event_buffers_by_type: DefaultDict[
            Type[Event], List[Event]
        ] = defaultdict(list)
        self._event_buffer: List[Event] = []

    def __iter__(self) -> Iterator[Event]:
        """Return an iterator for the event history"""
        return self._event_history.__iter__()

    def iter_events(self) -> Iterator[Event]:
        """Return an iterator to all the events in the buffer regardless of type"""
        return self._event_buffer.__iter__()

    def iter_events_of_type(self, event_type: Type[_ET]) -> Iterator[_ET]:
        """Return an iterator to the buffer of events for the given type"""
        # We probably shouldn't ignore this typing error, but I dont
        # know how to solve this right now
        return self._event_buffers_by_type[event_type].__iter__()  # type: ignore

    def emit(self, event: Event) -> None:
        """Emit a new event

        Parameters
        ----------
        event: Event
            The event that occurred
        """
        self._event_buffer.append(event)
        self._event_buffers_by_type[type(event)].append(event)

    def process_event_buffer(self) -> None:
        for event in self._event_buffer:
            for role in event.roles:
                self._per_gameobject[role.gid].append(event)
            self._event_history.append(event)

        self._event_buffer.clear()
        self._event_buffers_by_type.clear()

    def get_events_for(self, gid: int) -> List[Event]:
        """
        Get all the LifeEvents where the GameObject with the given gid played a role

        Parameters
        ----------
        gid: int
            ID of the GameObject to retrieve events for

        Returns
        -------
        List[Event]
            Events recorded for the given GameObject
        """
        return self._per_gameobject[gid]

    def to_dict(self) -> Dict[str, Any]:
        return {"events": [e.to_dict() for e in self._event_history]}


class RoleBinder(Protocol):
    """Function used to fill a RoleList"""

    def __call__(
        self, world: World, bindings: Optional[Dict[str, GameObject]] = None
    ) -> Optional[RoleList]:
        raise NotImplementedError


class RoleType:
    """Definition of a role that a GameObject can be bound to

    This class creates RoleInstances using a binder function that
    defines what preconditions need to be met by a GameObject, and
    retrieves one that meets those requirements.
    """

    __slots__ = "_binder_fn", "_name"

    def __init__(
        self,
        name: str,
        binder_fn: Optional[RoleTypeBindFn] = None,
    ) -> None:
        self._name: str = name
        self._binder_fn: Optional[RoleTypeBindFn] = binder_fn

    @property
    def name(self):
        """Get the name of this RoleType"""
        return self._name

    def fill_role(
        self, world: World, roles: RoleList, candidate: Optional[GameObject] = None
    ) -> Optional[RoleInstance]:
        """Try to create a RoleInstance from this RoleType

        Parameters
        ----------
        world: World
            The world instance
        roles: RoleList
            A collection of previously bound RoleInstances associated
            with this role
        candidate: GameObject, optional
            A GameObject to attempt to bind to this role

        Returns
        -------
        Optional[RoleInstance]
            Returns a RoleInstance instance with a gameobject or candidate
            bound to it. Or None if the binding failed
        """

        if self._binder_fn is None:
            if candidate is None:
                return None
            else:
                return RoleInstance(self._name, candidate.uid)

        if gameobject := self._binder_fn(world, roles, candidate):
            return RoleInstance(self._name, gameobject.uid)

        return None


class RoleTypeBindFn(Protocol):
    """Callable that returns a GameObject that meets requirements for a given Role"""

    def __call__(
        self, world: World, roles: RoleList, candidate: Optional[GameObject] = None
    ) -> Optional[GameObject]:
        raise NotImplementedError
