"""
social_rule.py

This module provides interfaces and classes to assist users in authoring rules that
influence how characters feel about each other.
"""
from __future__ import annotations

from typing import Any, Dict, Protocol, Type

from orrery.core.ecs import GameObject
from orrery.core.location_bias import ILocationBiasRule
from orrery.core.relationship import RelationshipStat


class ISocialRule(Protocol):
    """Interface for classes that implement social rules"""

    def __call__(
        self, subject: GameObject, target: GameObject
    ) -> Dict[Type[RelationshipStat], int]:
        """Evaluate the social rule and return the modifiers"""
        raise NotImplementedError


class SocialRuleFactory(Protocol):
    def __call__(self, **kwargs: Any) -> ILocationBiasRule:
        raise NotImplementedError
