from __future__ import annotations

from typing import Any, Dict, List, Optional, Type, TypeVar

from orrery.core.ecs import Component, GameObject, World

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


class EntityPrefab:
    """Data for creating a new entity and it's children

    Attributes
    ----------
    components: ComponentBundle
        Component configurations belonging to this entity
    children: List[EntityPrefab]
        Component information belonging to children of this entity
    """

    __slots__ = "components", "children"

    def __init__(
        self,
        components: ComponentBundle,
        children: Optional[List[EntityPrefab]] = None,
    ) -> None:
        """
        Parameters
        ----------
        components: ComponentBundle
            Component information for this entity
        children: List[EntityPrefab], optional
            A list of prefabs for children to be spawned with this
            entity. (defaults to None)
        """
        self.components: ComponentBundle = components
        self.children: List[EntityPrefab] = children if children else []

    def spawn(self, world: World) -> GameObject:
        """Spawn the prefab into the world and return the top-level entity

        Parameters
        ----------
        world: World
            The World instance to spawn this prefab into

        Returns
        -------
        GameObject
            A reference to the spawned entity
        """
        gameobject = self.components.spawn(world)

        for child in self.children:
            gameobject.add_child(child.spawn(world))

        return gameobject
