"""
location_frequency_rule.py

This module provides interface and classes that help characters determine
where within a settlement they choose to frequent
"""
from abc import ABC, abstractmethod
from typing import Callable

from orrery.core.ecs import GameObject


class ILocationBiasRule(ABC):
    """Interface for classes that implement location bias rules"""

    @abstractmethod
    def get_rule_name(self) -> str:
        """Get the name of this social rule"""
        raise NotImplementedError

    @abstractmethod
    def check_character(self, character: GameObject) -> bool:
        """Check if initiator passes preconditions"""
        raise NotImplementedError

    @abstractmethod
    def check_location(self, location: GameObject) -> bool:
        """Check if the target passes preconditions"""
        raise NotImplementedError

    @abstractmethod
    def evaluate(self, character: GameObject, location: GameObject) -> int:
        """Evaluate the social rule and return the modifiers"""
        raise NotImplementedError


class LocationBiasRule(ILocationBiasRule):
    """A parameterized social rule with a static modifier"""

    __slots__ = "name", "character_precondition", "location_precondition", "modifier"

    def __init__(
        self,
        name: str,
        character_precondition: Callable[[GameObject], bool],
        location_precondition: Callable[[GameObject], bool],
        modifier: int,
    ) -> None:
        self.name: str = name
        self.character_precondition: Callable[
            [GameObject], bool
        ] = character_precondition
        self.location_precondition: Callable[[GameObject], bool] = location_precondition
        self.modifier: int = modifier

    def get_rule_name(self) -> str:
        return self.name

    def check_character(self, character: GameObject) -> bool:
        return self.character_precondition(character)

    def check_location(self, location: GameObject) -> bool:
        return self.location_precondition(location)

    def evaluate(self, character: GameObject, location: GameObject) -> int:
        return self.modifier
