from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Optional, Protocol

from orrery.core.ecs import GameObject, World
from orrery.core.life_event import LifeEventInstance
from orrery.core.roles import RoleBinder, RoleList


class ActionEffectFn(Protocol):
    """Callback function called when an action is executed"""

    def __call__(self, world: World, roles: RoleList) -> None:
        raise NotImplementedError


class IActionInstance(ABC):
    """An abstract interface for all actions executed by characters="""

    @abstractmethod
    def execute(self, world: World) -> None:
        """Execute the action"""
        raise NotImplementedError


class ActionInstance(IActionInstance):
    """An instance of an action with all roles bound"""

    __slots__ = "name", "roles", "effect"

    def __init__(self, name: str, roles: RoleList, effect: ActionEffectFn) -> None:
        self.name: str = name
        self.roles: RoleList = roles
        self.effect: ActionEffectFn = effect

    def execute(self, world: World) -> None:
        self.effect(world, self.roles)


class IActionType(Protocol):
    """Interface for classes that create life events"""

    @abstractmethod
    def get_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def check_instantiator(self):
        ...

    @abstractmethod
    def instantiate(
        self, world: World, bindings: Optional[RoleList] = None
    ) -> Optional[LifeEventInstance]:
        """Attempts to create a new Event instance"""
        raise NotImplementedError


class ActionType:
    """An action that a character can perform

    This is adapted from:
    https://github.com/ianhorswill/CitySimulator/blob/master/Assets/Codes/Action/Actions/ActionType.cs

    Attributes
    ----------
    name: str
        Name of the LifeEventType and the LifeEvent it instantiates
    initiator_role: str
        The name of the role of the intitiator
    bind_fn: orrery.core.event.RoleBinder
        Function that attempt to bind roles for the LifeEvent
    effect: ActionEffectFn
        Function that executes changes to the world state base don the event
    """

    __slots__ = "name", "bind_fn", "effect", "initiator_role"

    def __init__(
        self,
        name: str,
        initiator_role: str,
        bind_fn: RoleBinder,
        effect: Optional[ActionEffectFn] = None,
    ) -> None:
        self.name: str = name
        self.initiator_role: str = initiator_role
        self.bind_fn: RoleBinder = bind_fn
        self.effect: Optional[ActionEffectFn] = effect

    def get_name(self) -> str:
        return self.name

    def instantiate(
        self,
        world: World,
        initiator: GameObject,
        other_roles: Optional[Dict[str, GameObject]] = None,
    ) -> Optional[ActionInstance]:
        """Attempt to create an instance of the action

        Parameters
        ----------
        world: World
            Neighborly world instance
        initiator: GameObject
            The character that is initiating this action
        other_roles: Dict[str, GameObject], optional
            Bindings of role names to GameObjects
        """
        bindings = {}

        if other_roles:
            bindings.update(other_roles)

        bindings[self.initiator_role] = initiator

        if roles := self.bind_fn(world, **bindings):
            return ActionInstance(self.name, roles, self.effect)
        return None

    @abstractmethod
    def execute(self, instance: ActionInstance) -> None:
        """Execute the action on an instance of the ActionType"""
        raise NotImplementedError
