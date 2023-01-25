"""
social_rule.py

This module provides interfaces and classes to assist users in authoring rules that
influence how characters feel about each other.
"""
from abc import ABC, abstractmethod
from typing import Callable, Dict

from orrery.core.ecs import GameObject


class ISocialRule(ABC):
    """Interface for classes that implement social rules"""

    @abstractmethod
    def get_rule_name(self) -> str:
        """Get the name of this social rule"""
        raise NotImplementedError

    @abstractmethod
    def check_initiator(self, gameobject: GameObject) -> bool:
        """Check if initiator passes preconditions"""
        raise NotImplementedError

    @abstractmethod
    def check_target(self, gameobject: GameObject) -> bool:
        """Check if the target passes preconditions"""
        raise NotImplementedError

    @abstractmethod
    def evaluate(self, initiator: GameObject, target: GameObject) -> Dict[str, int]:
        """Evaluate the social rule and return the modifiers"""
        raise NotImplementedError


class StaticSocialRule(ISocialRule):
    """A parameterized social rule with a static modifier"""

    __slots__ = "name", "initiator_precondition", "target_precondition", "modifier"

    def __init__(
        self,
        name: str,
        initiator_precondition: Callable[[GameObject], bool],
        target_precondition: Callable[[GameObject], bool],
        modifier: Dict[str, int],
    ) -> None:
        self.name: str = name
        self.initiator_precondition: Callable[
            [GameObject], bool
        ] = initiator_precondition
        self.target_precondition: Callable[[GameObject], bool] = target_precondition
        self.modifier: Dict[str, int] = modifier

    def get_rule_name(self) -> str:
        return self.name

    def check_initiator(self, gameobject: GameObject) -> bool:
        return self.initiator_precondition(gameobject)

    def check_target(self, gameobject: GameObject) -> bool:
        return self.target_precondition(gameobject)

    def evaluate(self, initiator: GameObject, target: GameObject) -> Dict[str, int]:
        return self.modifier
