"""
ecs.py

Custom Entity-Component implementation that blends the Unity-style GameObjects with the
ECS logic from the Python esper library and the Bevy Game Engine.

This ECS implementation is not thread-safe. It assumes that everything happens
sequentially on the same thread. There some features that were originally designed to
solve multithreading problems in Unity's Entities package. However, they are used here
more for adding reactivity.

Sources:
https://docs.unity3d.com/ScriptReference/GameObject.html
https://github.com/benmoran56/esper
https://github.com/bevyengine/bevy
https://bevy-cheatbook.github.io/programming/change-detection.html
https://bevy-cheatbook.github.io/programming/removal-detection.html
https://docs.unity3d.com/Packages/com.unity.entities@0.1/manual/index.html
"""
from __future__ import annotations

import dataclasses
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, Tuple, Type, TypeVar

import esper
from ordered_set import OrderedSet

logger = logging.getLogger(__name__)


_CT = TypeVar("_CT", bound="Component")
_RT = TypeVar("_RT", bound="Any")
_ST = TypeVar("_ST", bound="ISystem")


class ResourceNotFoundError(Exception):
    """Exception raised when attempting to access a resource that does not exist

    Attributes
    ----------
    resource_type: Type[Any]
        The type of the resource
    message: str
        An error message
    """

    __slots__ = "resource_type", "message"

    def __init__(self, resource_type: Type[Any]) -> None:
        """
        Parameters
        ----------
        resource_type: Type[Any]
            The type of the resource not found
        """
        super().__init__()
        self.resource_type: Type[Any] = resource_type
        self.message = f"Could not find resource with type: {resource_type.__name__}"

    def __str__(self) -> str:
        return self.message

    def __repr__(self) -> str:
        return "{}(resource_type={})".format(
            self.__class__.__name__, self.resource_type
        )


class GameObjectNotFoundError(Exception):
    """Exception raised when attempting to retrieve a GameObject that does not exist

    Attributes
    ----------
    gameobject_uid: int
        The unique ID of the desired GameObject
    message: str
        An error message
    """

    __slots__ = "gameobject_uid", "message"

    def __init__(self, gameobject_uid: int) -> None:
        """
        Parameters
        ----------
        gameobject_uid: int
            The unique ID of the desired GameObject
        """
        super().__init__()
        self.gameobject_uid: int = gameobject_uid
        self.message = f"Could not find GameObject with id: {gameobject_uid}."

    def __str__(self) -> str:
        return self.message

    def __repr__(self) -> str:
        return "{}(gameobject_uid={})".format(
            self.__class__.__name__, self.gameobject_uid
        )


class ComponentNotFoundError(Exception):
    """Exception raised when attempting to retrieve a component that does not exist

    Attributes
    ----------
    component_type: Type[Component]
        The type of component not found
    message: str
        An error message
    """

    __slots__ = "component_type", "message"

    def __init__(self, component_type: Type[Component]) -> None:
        """
        Parameters
        ----------
        component_type: Type[Component]
            The desired component type
        """
        super().__init__()
        self.component_type: Type[Component] = component_type
        self.message = "Could not find Component with type {}.".format(
            component_type.__name__
        )

    def __str__(self) -> str:
        return self.message

    def __repr__(self) -> str:
        return "{}(component_type={})".format(
            self.__class__.__name__,
            self.component_type.__name__,
        )


class GameObject:
    """A reference to an entity within the world

    GameObjects wrap a unique integer identifier provide an interface to manipulate
    an entity, its components, and its hierarchical relationship with other entities.

    Attributes
    ----------
    name: str
        The name of the GameObject
    children: List[GameObject]
        Other GameObjects that are below this one in the hierarchy
        and are removed when this GameObject is removed
    parent: Optional[GameObject]
        The GameObject that this GameObject is a child of
    """

    __slots__ = "_id", "name", "_world", "children", "parent", "_is_active"

    def __init__(
        self,
        unique_id: int,
        world: World,
        name: str = "",
    ) -> None:
        """
        Parameters
        ----------
        unique_id: int
            A unique identifier
        world: World
            The world instance that this GameObject belongs to
        name: str, optional
            An optional name to give to the GameObject
            (Defaults to 'GameObject(<unique_id>)')
        """
        self.name: str = name if name else f"GameObject({unique_id})"
        self._id: int = unique_id
        self._world: World = world
        self.parent: Optional[GameObject] = None
        self.children: List[GameObject] = []
        self._is_active: bool = True

    @property
    def uid(self) -> int:
        """Return GameObject's ID"""
        return self._id

    @property
    def world(self) -> World:
        """Return the world that this GameObject belongs to"""
        return self._world

    @property
    def exists(self) -> bool:
        """Return True if the GameObject still exists in the ECS"""
        return self.world.has_gameobject(self._id)

    @property
    def is_active(self) -> bool:
        """Return if this GameObject is active"""
        return self._is_active

    def set_active(self, is_active: bool) -> None:
        """Set the active status of the GameObject

        Parameters
        ----------
        is_active: bool
            desired active state
        """
        self._is_active = is_active

    def get_components(self) -> Tuple[Component, ...]:
        """Returns the component instances associated with this GameObject"""
        try:
            return self.world.get_components_for_entity(self.uid)
        except KeyError:
            # Ignore errors if gameobject is not found in esper ecs
            return ()

    def get_component_types(self) -> Tuple[Type[Component], ...]:
        """Returns the types of components attached to this character"""
        return tuple(map(lambda component: type(component), self.get_components()))

    def add_component(self, component: Component) -> None:
        """Add a component to this GameObject

        Parameters
        ----------
        component: Component
            An instance of a component

        Notes
        -----
        Adding components is an immediate operation.
        """
        self.world.add_component(self.uid, component)

    def remove_component(self, component_type: Type[Component]) -> None:
        """Remove a component from the GameObject

        Parameters
        ----------
        component_type: Type[Component]
            The type of the component to remove
        """
        self.world.remove_component(self.uid, component_type)

    def get_component(self, component_type: Type[_CT]) -> _CT:
        return self.world.get_component_for_entity(self.uid, component_type)

    def has_components(self, *component_types: Type[Component]) -> bool:
        return self.world.has_components(self.uid, *component_types)

    def has_component(self, component_type: Type[Component]) -> bool:
        """Check if this entity has a component of a given type"""
        return self.world.has_component(self.uid, component_type)

    def try_component(self, component_type: Type[_CT]) -> Optional[_CT]:
        try:
            return self.world.try_component_for_entity(self.uid, component_type)
        except KeyError:
            return None

    def add_child(self, gameobject: GameObject) -> None:
        """Add a GameObject as the child of this GameObject"""
        if gameobject.parent is not None:
            gameobject.parent.remove_child(gameobject)
        gameobject.parent = self
        self.children.append(gameobject)

    def remove_child(self, gameobject: GameObject) -> None:
        """Remove a GameObject as a child of this GameObject"""
        self.children.remove(gameobject)
        gameobject.parent = None

    def get_component_in_child(self, component_type: Type[_CT]) -> Tuple[int, _CT]:
        """Get a single instance of a component type attached to a child

        Performs a depth-first search of the children and their children and
        returns the first instance of the component type
        """

        stack = list(*self.children)
        checked: Set[GameObject] = set()

        while stack:
            entity = stack.pop()

            if entity in checked:
                continue

            checked.add(entity)

            if component := entity.try_component(component_type):
                return entity.uid, component

            for child in entity.children:
                stack.append(child)

        raise ComponentNotFoundError(component_type)

    def get_component_in_children(
        self, component_type: Type[_CT]
    ) -> List[Tuple[int, _CT]]:
        """Get all the instances of a component type attached to the immediate children of this GameObject"""
        results: List[Tuple[int, _CT]] = []

        stack = list(*self.children)
        checked: Set[GameObject] = set()

        while stack:
            entity = stack.pop()

            if entity in checked:
                continue

            checked.add(entity)

            if component := entity.try_component(component_type):
                results.append((entity.uid, component))

            for child in entity.children:
                stack.append(child)

        return results

    def destroy(self) -> None:
        """Remove the GameObject from its World instance"""
        self.world.delete_gameobject(self.uid)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the GameObject to a Dict"""
        ret = {
            "id": self.uid,
            "name": self.name,
            "parent": self.parent.uid if self.parent else -1,
            "children": [c.uid for c in self.children],
            "components": {
                c.__class__.__name__: c.to_dict() for c in self.get_components()
            },
        }

        return ret

    def __eq__(self, other: object) -> bool:
        if isinstance(other, GameObject):
            return self.uid == other.uid
        raise TypeError(f"Expected GameObject but was {type(object)}")

    def __int__(self) -> int:
        return self._id

    def __hash__(self) -> int:
        return self._id

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return "{}(id={}, name={}, parent={}, children={})".format(
            self.__class__.__name__, self.uid, self.name, self.parent, self.children
        )


# class IECSCommand(Protocol):
#     """A Command object that makes a change to the ECS World instance"""
#
#     def get_type(self) -> str:
#         """Return the type of this command"""
#         raise NotImplementedError
#
#     def apply(self, world: World) -> None:
#         """Apply the affects of this command to the world state"""
#         raise NotImplementedError
#
#
# @dataclasses.dataclass(frozen=True)
# class AddComponentCommand:
#     """This command adds a component to a gameobject
#
#     Attributes
#     ----------
#     gameobject_uid: int
#         The unique identifier of a GameObject
#     component: Component
#         The component to add to the GameObject
#     """
#
#     gameobject_uid: int
#     component: Component
#
#     def get_type(self) -> str:
#         return self.__class__.__name__
#
#     def apply(self, world: World) -> None:
#         world.add_component(self.gameobject_uid, self.component)
#
#
# @dataclasses.dataclass(frozen=True)
# class RemoveComponentCommand:
#     """
#     This command removes a component from a gameobject
#
#     Attributes
#     ----------
#     gameobject_uid: int
#         The unique identifier of a GameObject
#     component_type: Type[Component]
#         The component type to remove from the GameObject
#     """
#
#     gameobject_uid: int
#     component_type: Type[Component]
#
#     def get_type(self) -> str:
#         return self.__class__.__name__
#
#     def apply(self, world: World) -> None:
#         try:
#             gameobject = world.get_gameobject(self.gameobject_uid)
#             if not gameobject.has_component(self.component_type):
#                 return
#             world.remove_component(gameobject.uid, self.component_type)
#         except GameObjectNotFoundError:
#             return
#
#
# @dataclasses.dataclass(frozen=True)
# class DeleteGameObjectCommand:
#     """This command removes a gameobject from the world
#
#     Attributes
#     ----------
#     gameobject_uid: int
#         The unique identifier of a GameObject
#     """
#
#     gameobject_uid: int
#
#     def get_type(self) -> str:
#         return self.__class__.__name__
#
#     def apply(self, world: World) -> None:
#         world.delete_gameobject(self.gameobject_uid)


class Component(ABC):
    """Components are collections of related data attached to GameObjects"""

    __slots__ = "_gameobject"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__()
        self._gameobject: Optional[GameObject] = None

    @property
    def gameobject(self) -> GameObject:
        """Return the GameObject this component is attached to"""
        if self._gameobject is None:
            raise TypeError("Component's GameObject is None")
        return self._gameobject

    def set_gameobject(self, gameobject: Optional[GameObject]) -> None:
        """
        Set the gameobject instance for this component

        Parameters
        ----------
        gameobject: Optional[GameObject]
            The GameObject instance or None if being removed from a GameObject
        """
        self._gameobject = gameobject

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the component to a dict"""
        return {}


class ISystem(ABC, esper.Processor):
    """Abstract base class implementation for ECS systems"""

    # We have to re-type the 'world' class variable because
    # it is declared as 'Any' by esper, and we need it to
    # be of type World
    world: World  # type: ignore


class IComponentFactory(ABC):
    """Abstract base class for factory object that create Component instances"""

    @abstractmethod
    def create(self, world: World, **kwargs: Any) -> Component:
        """
        Create an instance of a component

        Parameters
        ----------
        world: World
            Reference to the World object
        **kwargs: Dict[str, Any]
            Additional keyword parameters

        Returns
        -------
        Component
            Component instance
        """
        raise NotImplementedError


@dataclasses.dataclass(frozen=True)
class ComponentInfo:
    """Information about component classes registered with a World instance

    We use this information to lookup string names mapped to component types,
    and to find the proper factory to use when constructing a component instance
    from a data file or ComponentBundle

    Attributes
    ----------
    name: str
        The name mapped to this component type
    component_type: Type[Component]
        The component class
    factory: IComponentFactory
        A factory instance used to construct the given component type
    """

    name: str
    component_type: Type[Component]
    factory: IComponentFactory


class DefaultComponentFactory(IComponentFactory):
    """
    Constructs instances of a component only using keyword parameters

    Attributes
    ----------
    component_type: Type[Component]
        The type of component that this factory will create
    """

    __slots__ = "component_type"

    def __init__(self, component_type: Type[Component]) -> None:
        super().__init__()
        self.component_type: Type[Component] = component_type

    def create(self, world: World, **kwargs: Any) -> Component:
        """Create a new instance of the component_type using keyword arguments"""
        return self.component_type(**kwargs)


class World:
    """
    Manages Gameobjects, Systems, and resources for the simulation

    Attributes
    ----------
    _ecs: esper.World
        Esper ECS instance used for efficiency
    _gameobjects: Dict[int, GameObject]
        Mapping of GameObjects to unique identifiers
    _dead_gameobjects: List[int]
        List of identifiers for GameObject to remove after
        the latest time step
    _resources: Dict[Type, Any]
        Global resources shared by systems in the ECS
    """

    __slots__ = (
        "_ecs",
        "_gameobjects",
        "_dead_gameobjects",
        "_resources",
        "_component_types",
        "_component_factories",
        "_removed_components",
        "_added_components",
    )

    def __init__(self) -> None:
        self._ecs: esper.World = esper.World()
        self._gameobjects: Dict[int, GameObject] = {}
        self._dead_gameobjects: OrderedSet[int] = OrderedSet([])
        self._resources: Dict[Type[Any], Any] = {}
        self._component_types: Dict[str, ComponentInfo] = {}
        self._component_factories: Dict[Type[Component], IComponentFactory] = {}
        self._removed_components: Dict[Type[Component], OrderedSet[int]] = {}
        self._added_components: Dict[Type[Component], OrderedSet[int]] = {}

    def spawn_gameobject(
        self, components: Optional[List[Component]] = None, name: Optional[str] = None
    ) -> GameObject:
        """Create a new gameobject and attach any given component instances"""
        components_to_add = components if components else []

        entity_id = self._ecs.create_entity(*components_to_add)

        gameobject = GameObject(
            unique_id=entity_id,
            world=self,
            name=(name if name else f"GameObject({entity_id})"),
        )

        self._gameobjects[gameobject.uid] = gameobject

        # Since we did not add the component through the GameObject's add_component
        # method, we have to set the references here
        for c in components_to_add:
            c.set_gameobject(gameobject)

        return gameobject

    def get_gameobject(self, gid: int) -> GameObject:
        """Retrieve the GameObject with the given id"""
        try:
            return self._gameobjects[gid]
        except KeyError:
            raise GameObjectNotFoundError(gid)

    def get_gameobjects(self) -> List[GameObject]:
        """Get all gameobjects"""
        return list(self._gameobjects.values())

    def has_gameobject(self, gid: int) -> bool:
        """Check that a GameObject with the given id exists"""
        return gid in self._gameobjects

    def delete_gameobject(self, gid: int) -> None:
        """Remove gameobject from world"""
        gameobject = self._gameobjects[gid]

        gameobject.set_active(False)

        self._dead_gameobjects.append(gid)

        # Recursively remove all children
        for child in gameobject.children:
            self.delete_gameobject(child.uid)

    def add_component(self, gid: int, component: Component) -> None:
        """Add a component to an entity"""
        component.set_gameobject(self._gameobjects[gid])
        component_type = type(component)
        if component_type not in self._added_components:
            self._added_components[component_type] = OrderedSet([])
        self._added_components[component_type].append(int(gid))
        self._ecs.add_component(int(gid), component)

    def remove_component(self, gid: int, component_type: Type[Component]) -> None:
        """Remove a component from an entity"""
        if component_type not in self._removed_components:
            self._removed_components[component_type] = OrderedSet([])
        self._removed_components[component_type].append(int(gid))
        try:
            self._ecs.remove_component(int(gid), component_type)
        except KeyError:
            # This will throw a key error if the GameObject does not
            # have any components.
            return

    def get_component(self, component_type: Type[_CT]) -> List[Tuple[int, _CT]]:
        """Get all the gameobjects that have a given component type"""
        return self._ecs.get_component(component_type)

    def get_component_for_entity(self, guid: int, component_type: Type[_CT]) -> _CT:
        """Return the component type attached to an entity

        Parameters
        ----------
        guid: int
            The entity to check on
        component_type: Type[_CT]
            The component type to retrieve

        Returns
        -------
        _CT
            The instance of the given component type
        """
        try:
            return self._ecs.component_for_entity(guid, component_type)
        except KeyError:
            raise ComponentNotFoundError(component_type)

    def try_component_for_entity(
        self, guid: int, component_type: Type[_CT]
    ) -> Optional[_CT]:
        """Attempt to return the component type attached to an entity

        Parameters
        ----------
        guid: int
            The entity to check on
        component_type: Type[_CT]
            The component type to retrieve

        Returns
        -------
        Optional[_CT]
            The instance of the given component type
        """
        try:
            return self._ecs.try_component(guid, component_type)
        except KeyError:
            return None

    def get_components(
        self, *component_types: Type[_CT]
    ) -> List[Tuple[int, List[_CT]]]:
        """Get all game objects with the given components"""
        return self._ecs.get_components(*component_types)  # type: ignore

    def has_components(self, guid: int, *component_types: Type[_CT]) -> bool:
        try:
            return self._ecs.has_components(guid, *component_types)
        except KeyError:
            return False

    def has_component(self, guid: int, component_type: Type[_CT]) -> bool:
        try:
            return self._ecs.has_component(guid, component_type)
        except KeyError:
            return False

    def get_components_for_entity(self, guid: int) -> Tuple[_CT, ...]:
        """Get the instances of the component types on the given entity

        Parameters
        ----------
        guid: int
            The entity to check on

        Returns
        -------
        Tuple[Component, ...]
            Component instances
        """
        return self._ecs.components_for_entity(guid)

    def _clear_dead_gameobjects(self) -> None:
        """Delete gameobjects that were removed from the world"""
        for gameobject_id in self._dead_gameobjects:
            if len(self._gameobjects[gameobject_id].get_components()) > 0:
                self._ecs.delete_entity(gameobject_id, True)

            gameobject = self._gameobjects[gameobject_id]

            if gameobject.parent is not None:
                gameobject.parent.remove_child(gameobject)

            del self._gameobjects[gameobject_id]
        self._dead_gameobjects.clear()

    def add_system(self, system: ISystem, priority: int = 0) -> None:
        """Add a System instance to the World"""
        self._ecs.add_processor(system, priority=priority)
        system.world = self

    def get_system(self, system_type: Type[_ST]) -> Optional[_ST]:
        """Get a System of the given type"""
        return self._ecs.get_processor(system_type)  # type: ignore

    def remove_system(self, system_type: Type[ISystem]) -> None:
        """Remove a System from the World"""
        self._ecs.remove_processor(system_type)

    def step(self, **kwargs: Any) -> None:
        """Call the process method on all systems"""
        self._clear_dead_gameobjects()
        self._ecs.process(**kwargs)  # type: ignore
        self._removed_components.clear()
        self._added_components.clear()

    def add_resource(self, resource: Any) -> None:
        """Add a global resource to the world"""
        resource_type = type(resource)
        if resource_type in self._resources:
            logger.warning(f"Replacing existing resource of type: {resource_type}")
        self._resources[resource_type] = resource

    def remove_resource(self, resource_type: Any) -> None:
        """remove a global resource to the world"""
        try:
            del self._resources[resource_type]
        except KeyError:
            raise ResourceNotFoundError(resource_type)

    def get_resource(self, resource_type: Type[_RT]) -> _RT:
        """Add a global resource to the world"""
        try:
            return self._resources[resource_type]
        except KeyError:
            raise ResourceNotFoundError(resource_type)

    def has_resource(self, resource_type: Any) -> bool:
        """Return true if the world has the given resource"""
        return resource_type in self._resources

    def try_resource(self, resource_type: Type[_RT]) -> Optional[_RT]:
        """Attempt to get resource with type. Return None if not found"""
        return self._resources.get(resource_type)

    def get_all_resources(self) -> List[Any]:
        """Get all resources attached to this World instance"""
        return list(self._resources.values())

    def get_factory(self, component_type: Type[Component]) -> IComponentFactory:
        """Return the factory associate with a component type"""
        return self._component_factories[component_type]

    def get_component_info(self, component_name: str) -> ComponentInfo:
        return self._component_types[component_name]

    def register_component(
        self,
        component_type: Type[Component],
        name: Optional[str] = None,
        factory: Optional[IComponentFactory] = None,
    ) -> None:
        """
        Register component with the engine
        """
        component_name = name if name is not None else component_type.__name__

        self._component_types[component_name] = ComponentInfo(
            name=component_name,
            component_type=component_type,
            factory=(
                factory
                if factory is not None
                else DefaultComponentFactory(component_type)
            ),
        )

        self._component_factories[component_type] = (
            factory if factory is not None else DefaultComponentFactory(component_type)
        )

    def get_removed_component(self, component_type: Type[Component]) -> List[int]:
        """Return the IDs of GameObjects that had the given component type added

        Parameters
        ----------
        component_type: Type[Component]
            The component type to check for

        Returns
        -------
        List[int]
            The ID of GameObjects
        """
        return list(self._removed_components.get(component_type, []))

    def get_added_component(self, component_type: Type[Component]) -> List[int]:
        """Return the IDs of GameObjects that had the given component type removed

        Parameters
        ----------
        component_type: Type[Component]
            The component type to check for

        Returns
        -------
        List[int]
            The ID of GameObjects
        """
        return list(self._added_components.get(component_type, []))
