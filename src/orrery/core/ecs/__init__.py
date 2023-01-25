"""
Entity-Component System

This package contains functionality for the entity-component system. It has definitions
for entities, systems, the world, queries, and entity prefabs.
"""

from .ecs import *
from .prefab import *
from .query import *

__all__ = [
    "ecs",
    "prefab",
    "query"
]
