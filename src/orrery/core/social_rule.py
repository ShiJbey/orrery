"""
social_rule.py

This module provides interfaces and classes to assist users in authoring rules that
influence how characters feel about each other.
"""
from abc import ABC, abstractmethod
from typing import List, Protocol

from orrery.components.relationship import IRelationshipModifier, Relationship
from orrery.core.ecs import GameObject, World


class ISocialRule(ABC):
    """
    Social Rules apply modifications to character relationships based on certain
    preconditions
    """

    @abstractmethod
    def get_uid(self) -> str:
        """Return the unique identifier of the modifier"""
        raise NotImplementedError

    @abstractmethod
    def check_preconditions(self, world: World, *gameobjects: GameObject) -> bool:
        """
        Check if a given condition hold true to apply the modifiers

        Parameters
        ----------
        world: World
            The World instance for the simulation
        *gameobjects: GameObject
            The GameObject instances to check the precondition against

        Returns
        -------
        bool
            Return True if the precondition passes
        """
        raise NotImplementedError

    @abstractmethod
    def activate(
        self,
        world: World,
        subject: GameObject,
        target: GameObject,
        relationship: GameObject,
    ) -> None:
        """
        Apply any modifiers associated with the social rule

        Parameters
        ----------
        world: World
            The world instance for the simulation
        subject: GameObject
            The GameObject that owns the relationship instance being modified
        target: GameObject
            The GameObject that is the target of the relationship instance
        relationship: Relationship
            The Relationship instance to modify
        """
        raise NotImplementedError

    @abstractmethod
    def deactivate(self, relationship: GameObject) -> None:
        """
        Remove the affects of this social rule from the given Relationship

        Parameters
        ----------
        relationship: Relationship
            The relationship instance to remove effects from
        """
        raise NotImplementedError


class SocialRulePreconditionFn(Protocol):
    """Callable that checks if a condition is true between gameobjects"""

    def __call__(self, world: World, *gameobjects: GameObject) -> bool:
        raise NotImplementedError


class SocialRule(ISocialRule):
    """
    Simple implementation of social rules

    Attributes
    ----------
    precondition: SocialRulePreconditionFn
        A function that checks if a condition holds true between GameObjects
    modifiers: List[IRelationshipModifier]
        Modifiers to apply to a Relationship instance
    name: str
        The name of the social rule
    """

    __slots__ = "precondition", "modifiers", "name"

    def __init__(
        self,
        name: str,
        precondition: SocialRulePreconditionFn,
        modifiers: List[IRelationshipModifier],
    ) -> None:
        super().__init__()
        self.name: str = name
        self.precondition: SocialRulePreconditionFn = precondition
        self.modifiers: List[IRelationshipModifier] = modifiers

    def get_uid(self) -> str:
        return self.name

    def check_preconditions(self, world: World, *gameobjects: GameObject) -> bool:
        return self.precondition(world, *gameobjects)

    def activate(
        self,
        world: World,
        subject: GameObject,
        target: GameObject,
        relationship: GameObject,
    ) -> None:
        for modifier in self.modifiers:
            relationship.get_component(Relationship).add_modifier(modifier)
            modifier.activate(relationship.get_component(Relationship))

    def deactivate(self, relationship: GameObject) -> None:
        for modifier in self.modifiers:
            r = relationship.get_component(Relationship)
            if modifier.get_uid() in r.active_modifiers:
                r.remove_modifier(modifier)
                modifier.deactivate(r)
