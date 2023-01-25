from __future__ import annotations

from typing import Any, Dict, List, TypeVar

import pydantic

from orrery.core.ecs import GameObject, World

_KT = TypeVar("_KT")


class EntityPrefab(pydantic.BaseModel):
    """Data for creating a new entity and it's children

    Attributes
    ----------
    components: Dict[str, Dict[str, Any]]
        Names of components mapped to keyword arguments passed to their registered
        factory instance
    children: List[EntityPrefab]
        Information about child prefabs to instantiate along with this one
    """

    components: Dict[str, Dict[str, Any]] = pydantic.Field(default_factory=dict)
    children: List[EntityPrefab] = pydantic.Field(default_factory=list)

    def spawn(self, world: World) -> GameObject:
        """Spawn the prefab into the world and return the root-level entity

        Parameters
        ----------
        world: World
            The World instance to spawn this prefab into

        Returns
        -------
        GameObject
            A reference to the spawned entity
        """

        # spawn the root gameobject
        gameobject = world.spawn_gameobject()

        for component_name, options in self.components.items():
            gameobject.add_component(
                world.get_component_info(component_name).factory.create(
                    world, **options
                )
            )

        for child in self.children:
            gameobject.add_child(child.spawn(world))

        return gameobject
