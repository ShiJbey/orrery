"""
Entity-Component System

This package contains functionality for the entity-component system. It has definitions
for entities, systems, the world, queries, and entity prefabs.
"""

from .ecs import (
    Component,
    ComponentNotFoundError,
    GameObject,
    GameObjectNotFoundError,
    IComponentFactory,
    ISystem,
    ResourceNotFoundError,
    World,
)
from .prefab import EntityPrefab
from .query import Query, QueryBuilder, QueryFilterFn, QueryFromFn, QueryGetFn

__all__ = [
    "Component",
    "ComponentNotFoundError",
    "GameObject",
    "GameObjectNotFoundError",
    "IComponentFactory",
    "ISystem",
    "ResourceNotFoundError",
    "World",
    "EntityPrefab",
    "Query",
    "QueryBuilder",
    "QueryFilterFn",
    "QueryFromFn",
    "QueryGetFn",
]
