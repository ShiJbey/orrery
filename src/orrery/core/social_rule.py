"""
social_rule.py

This module provides interfaces and classes to assist users in authoring rules that
influence how characters feel about each other.
"""
from typing import Dict, Protocol, Type

from orrery.core.ecs import GameObject
from orrery.core.relationship import RelationshipStat


class ISocialRule(Protocol):
    """Interface for classes that implement social rules"""

    def __call__(
        self, subject: GameObject, target: GameObject
    ) -> Dict[Type[RelationshipStat], int]:
        """Evaluate the social rule and return the modifiers"""
        raise NotImplementedError
