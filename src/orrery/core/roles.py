from __future__ import annotations

from typing import Any, Dict, Iterable, Iterator, List, Optional, Protocol

from orrery.core.ecs import GameObject, World


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
    ) -> Optional[Role]:
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
        Optional[Role]
            Returns a RoleInstance instance with a gameobject or candidate
            bound to it. Or None if the binding failed
        """

        if self._binder_fn is None:
            if candidate is None:
                return None
            else:
                return Role(self._name, candidate)

        if gameobject := self._binder_fn(world, roles, candidate):
            return Role(self._name, gameobject)

        return None


class RoleTypeBindFn(Protocol):
    """Callable that returns a GameObject that meets requirements for a given Role"""

    def __call__(
        self, world: World, roles: RoleList, candidate: Optional[GameObject] = None
    ) -> Optional[GameObject]:
        raise NotImplementedError


class RoleBinder(Protocol):
    """Function used to fill a RoleList"""

    def __call__(
        self,
        world: World,
        bindings: Optional[RoleList] = None,
    ) -> Optional[RoleList]:
        raise NotImplementedError


class Role:
    """A role name bound to a GameObject ID"""

    __slots__ = "_name", "_gameobject"

    def __init__(self, name: str, gameobject: GameObject) -> None:
        self._name: str = name
        self._gameobject: GameObject = gameobject

    @property
    def name(self) -> str:
        """Get the name of the role"""
        return self._name

    @property
    def gameobject(self) -> GameObject:
        """Get the ID of the GameObject bound to the role"""
        return self._gameobject

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "gameobject": self.gameobject.uid}

    def __str__(self) -> str:
        return f"({self.name}: {self.gameobject})"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, gid={self.gameobject})"


class RoleList:
    """A collection of roles for an event"""

    __slots__ = "_roles", "_sorted_roles"

    def __init__(
        self, roles: Optional[Iterable[Role]] = None
    ) -> None:
        self._roles: List[Role] = []
        self._sorted_roles: Dict[str, List[Role]] = {}

        if roles:
            for role in roles:
                self.add_role(role)

    def add_role(self, role: Role) -> None:
        """Add role to the event"""
        self._roles.append(role)
        if role.name not in self._sorted_roles:
            self._sorted_roles[role.name] = []
        self._sorted_roles[role.name].append(role)

    def get_all(self, role_name: str) -> List[GameObject]:
        """Return the IDs of all GameObjects bound to the given role name"""
        return [role.gameobject for role in self._sorted_roles[role_name]]

    def get(self, role_name: str) -> Optional[GameObject]:
        if role_name in self._sorted_roles:
            return self._sorted_roles[role_name][0].gameobject
        return None

    def __len__(self) -> int:
        return len(self._roles)

    def __bool__(self) -> int:
        return bool(self._roles)

    def __getitem__(self, role_name: str) -> GameObject:
        return self._sorted_roles[role_name][0].gameobject

    def __iter__(self) -> Iterator[Role]:
        return self._roles.__iter__()

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return "[{}]".format(", ".join([str(role) for role in self._roles]))
