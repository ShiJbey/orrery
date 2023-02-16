"""
location_frequency_rule.py

This module provides interface and classes that help characters determine
where within a settlement they choose to frequent
"""
from typing import Optional, Protocol

from orrery.core.ecs import GameObject


class ILocationBiasRule(Protocol):
    """Interface for classes that implement location bias rules"""

    def __call__(self, character: GameObject, location: GameObject) -> Optional[int]:
        """Evaluate the bias rule and return the modifier"""
        raise NotImplementedError
