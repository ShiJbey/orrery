"""
Custom Entity-Component implementation that blends
the Unity-style GameObjects with the ECS logic from the
Python esper library and the Bevy Game Engine.

Sources:
https://docs.unity3d.com/ScriptReference/GameObject.html
https://github.com/benmoran56/esper
https://github.com/bevyengine/bevy
"""
from __future__ import annotations

import dataclasses
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, List, Optional, Protocol, Tuple, Type, TypeVar

import esper
from ordered_set import OrderedSet

logger = logging.getLogger(__name__)


_CT = TypeVar("_CT", bound="Component")
_RT = TypeVar("_RT", bound="Any")
_ST = TypeVar("_ST", bound="ISystem")


class ResourceNotFoundError(Exception):
    """Exception raised when attempting to access a resource that does not exist"""

    __slots__ = "resource_type"

    def __init__(self, resource_type: Type[Any]) -> None:
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
    """Exception raised when attempting to retrieve a GameObject that does not exist"""

    __slots__ = "gameobject_uid"

    def __init__(self, gameobject_uid: int) -> None:
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
    """Exception raised when attempting to retrieve a component that does not exist"""

    __slots__ = "component_type", "message"

    def __init__(self, component_type: Type[Component]) -> None:
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
    """
    Collections of components that share are unique identifier
    and represent entities within the game world

    Attributes
    ----------
    name: str
        The name of the GameObject
    children: List[GameObject]
        Other GameObjects that are below this one in the hierarchy
        and are removed when the parent is removed
    parent: Optional[GameObject]
        The GameObject that this GameObject is a child of
    """

    __slots__ = "_id", "name", "_world", "children", "parent"

    def __init__(
        self,
        unique_id: int,
        world: World,
        name: Optional[str] = None,
        components: Optional[Iterable[Component]] = None,
    ) -> None:
        self.name: str = name if name else f"GameObject ({unique_id})"
        self._id: int = unique_id
        self._world: World = world
        self.parent: Optional[GameObject] = None
        self.children: List[GameObject] = []

        if components:
            for component in components:
                self.add_component(component)

    @property
    def uid(self) -> int:
        """Return GameObject's ID"""
        return self._id

    @property
    def world(self) -> World:
        """Return the world that this GameObject belongs to"""
        return self._world

    def get_components(self) -> Tuple[Component, ...]:
        """Returns the component instances associated with this GameObject"""
        try:
            return self.world.ecs.components_for_entity(self.uid)
        except KeyError:
            # Ignore errors if gameobject is not found in esper ecs
            return ()

    def get_component_types(self) -> Tuple[Type[Component], ...]:
        """Returns the types of components attached to this character"""
        return tuple(map(lambda component: type(component), self.get_components()))

    def add_component(self, component: Component) -> None:
        """Add a component to this GameObject"""
        component.set_gameobject(self)
        self.world.ecs.add_component(self.uid, component)

    def remove_component(
        self, component_type: Type[Component], immediate: bool = True
    ) -> None:
        """Add a component to this GameObject"""
        try:
            command = RemoveComponentCommand(self.uid, component_type)

            if immediate:
                command.apply(self.world)
            else:
                self.world.command_queue.append(command)
        except KeyError:
            return

    def get_component(self, component_type: Type[_CT]) -> _CT:
        try:
            return self.world.ecs.component_for_entity(self.uid, component_type)  # type: ignore
        except KeyError:
            raise ComponentNotFoundError(component_type)

    def has_component(self, *component_type: Type[Component]) -> bool:
        try:
            return all(
                [
                    self.world.ecs.try_component(self.uid, ct) is not None
                    for ct in component_type
                ]
            )
        except KeyError:
            return False

    def try_component(self, component_type: Type[_CT]) -> Optional[_CT]:
        try:
            return self.world.ecs.try_component(self.uid, component_type)  # type: ignore
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
        """Get a single instance of a component type attached to a child"""
        for child in self.children:
            if component := child.try_component(component_type):
                return child.uid, component
        raise ComponentNotFoundError(component_type)

    def get_component_in_children(
        self, component_type: Type[_CT]
    ) -> List[Tuple[int, _CT]]:
        """Get all the instances of a component type attached to the immediate children of this GameObject"""
        results: List[Tuple[int, _CT]] = []
        for child in self.children:
            if component := child.try_component(component_type):
                results.append((child.uid, component))
        return results

    def destroy(self) -> None:
        self.world.delete_gameobject(self.uid)

    def to_dict(self) -> Dict[str, Any]:
        ret = {
            "id": self.uid,
            "name": self.name,
            "components": {
                c.__class__.__name__: c.to_dict() for c in self.get_components()
            },
        }

        return ret

    def __eq__(self, other: object) -> bool:
        if isinstance(other, GameObject):
            return self.uid == other.uid
        raise TypeError(f"Expected GameObject but was {type(object)}")

    def __hash__(self) -> int:
        return self._id

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"GameObject(id={self.uid}, name={self.name})"


class IECSCommand(Protocol):
    """A Command object that makes a change to the ECS World instance"""

    def get_type(self) -> str:
        """Return the type of this command"""
        raise NotImplementedError

    def apply(self, world: World) -> None:
        """Apply the affects of this command to the world state"""
        raise NotImplementedError


@dataclasses.dataclass(frozen=True)
class AddComponentCommand:
    """This command adds a component to a gameobject

    Attributes
    ----------
    gameobject_uid: int
        The unique identifier of a GameObject
    component: Component
        The component to add to the GameObject
    """

    gameobject_uid: int
    component: Component

    def get_type(self) -> str:
        return self.__class__.__name__

    def apply(self, world: World) -> None:
        world.ecs.add_component(self.gameobject_uid, self.component)


@dataclasses.dataclass(frozen=True)
class RemoveComponentCommand:
    """
    This command removes a component from a gameobject

    Attributes
    ----------
    gameobject_uid: int
        The unique identifier of a GameObject
    component_type: Type[Component]
        The component type to remove from the GameObject
    """

    gameobject_uid: int
    component_type: Type[Component]

    def get_type(self) -> str:
        return self.__class__.__name__

    def apply(self, world: World) -> None:
        try:
            gameobject = world.get_gameobject(self.gameobject_uid)
            if not gameobject.has_component(self.component_type):
                return
            world.ecs.remove_component(gameobject.uid, self.component_type)
        except GameObjectNotFoundError:
            return


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
        "_command_queue",
        "_component_types",
        "_component_factories",
    )

    def __init__(self) -> None:
        self._ecs: esper.World = esper.World()
        self._gameobjects: Dict[int, GameObject] = {}
        self._dead_gameobjects: OrderedSet[int] = OrderedSet([])
        self._resources: Dict[Type[Any], Any] = {}
        self._command_queue: List[IECSCommand] = []
        self._component_types: Dict[str, ComponentInfo] = {}
        self._component_factories: Dict[Type[Component], IComponentFactory] = {}

    @property
    def ecs(self) -> esper.World:
        return self._ecs

    @property
    def command_queue(self) -> List[IECSCommand]:
        return self._command_queue

    def spawn_gameobject(
        self, components: Optional[List[Component]] = None, name: Optional[str] = None
    ) -> GameObject:
        """Create a new gameobject and attach any given component instances"""
        entity_id = self._ecs.create_entity(*components if components else [])
        gameobject = GameObject(
            unique_id=entity_id,
            world=self,
            name=(name if name else f"GameObject({entity_id})"),
        )
        self._gameobjects[gameobject.uid] = gameobject
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

    def try_gameobject(self, gid: int) -> Optional[GameObject]:
        """Retrieve the GameObject with the given id"""
        return self._gameobjects.get(gid)

    def delete_gameobject(self, gid: int) -> None:
        """Remove gameobject from world"""
        self._dead_gameobjects.append(gid)

        # Recursively remove all children
        for child in self._gameobjects[gid].children:
            self.delete_gameobject(child.uid)

    def get_component(self, component_type: Type[_CT]) -> List[Tuple[int, _CT]]:
        """Get all the gameobjects that have a given component type"""
        return self._ecs.get_component(component_type)  # type: ignore

    def get_components(
        self, *component_types: Type[_CT]
    ) -> List[Tuple[int, List[_CT]]]:
        """Get all game objects with the given components"""
        return self._ecs.get_components(*component_types)  # type: ignore

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

    def clear_command_queue(self) -> None:
        while self._command_queue:
            command = self._command_queue.pop(0)
            command.apply(self)

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
        self.clear_command_queue()

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

    def __repr__(self) -> str:
        return "World(gameobjects={}, resources={})".format(
            len(self._gameobjects),
            list(self._resources.values()),
        )


_KT = TypeVar("_KT")


class ComponentBundle:
    """"""

    __slots__ = "components"

    def __init__(self, components: Dict[Type[Component], Dict[str, Any]]) -> None:
        self.components = components

    @staticmethod
    def _merge_overrides(
        source: Dict[_KT, Any], other: Dict[_KT, Any]
    ) -> Dict[_KT, Any]:
        """
        Merges two dictionaries of overrides together

        Parameters
        ----------
        source: Dict[_KT, Any]
            Dictionary with initial field values

        other: Dict[_KT, Any]
            Dictionary with fields to override in the source dict

        Returns
        -------
        Dict[_KT, Any]
            New dictionary with fields in source overwritten
            with values from the other
        """
        merged_dict = {**source}

        for key, value in other.items():
            if isinstance(value, dict):
                # get node or create one
                node = merged_dict.get(key, {})
                merged_dict[key] = ComponentBundle._merge_overrides(node, value)  # type: ignore
            else:
                merged_dict[key] = value

        return merged_dict

    def spawn(
        self,
        world: World,
        overrides: Optional[Dict[Type[Component], Dict[str, Any]]] = None,
    ) -> GameObject:
        """Create a new gameobject instance"""
        merged_options: Dict[
            Type[Component], Dict[str, Any]
        ] = ComponentBundle._merge_overrides(
            self.components, (overrides if overrides else {})
        )

        gameobject = world.spawn_gameobject()

        for component_type, _ in self.components.items():
            component_factory = world.get_factory(component_type)
            gameobject.add_component(
                component_factory.create(
                    world,
                    **merged_options.get(component_type, {}),
                )
            )

        return gameobject
