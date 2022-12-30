import re
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Protocol

from orrery.core.ecs import GameObject, World
from orrery.core.relationship import IRelationshipModifier, Relationship


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
        relationship: Relationship,
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
    def deactivate(self, relationship: Relationship) -> None:
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
        super(ISocialRule, self).__init__()
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
        relationship: Relationship,
    ) -> None:
        for modifier in self.modifiers:
            relationship.add_modifier(modifier)
            modifier.activate(relationship)

    def deactivate(self, relationship: Relationship) -> None:
        for modifier in self.modifiers:
            if modifier.get_uid() in relationship.active_modifiers:
                relationship.remove_modifier(modifier)
                modifier.deactivate(relationship)


class SocialRuleLibrary:
    """
    Repository of ISocialRule instances to use during the simulation.

    Attributes
    ----------
    _all_rules: Dict[str, ISocialRule]
        All the rules added to the library, including ones not actively used in
        relationship calculations. (allows filtering)
    _active_rules: List[ISocialRule]
        List of the rules that are actively used for relationship calculations
    _active_rule_names: List[str]
        List of regular expression strings that correspond to rules to
        set as active for use in relationship calculations
    """

    __slots__ = "_all_rules", "_active_rules", "_active_rule_names"

    def __init__(
        self,
        rules: Optional[List[ISocialRule]] = None,
        active_rules: Optional[List[str]] = None,
    ) -> None:
        self._all_rules: Dict[str, ISocialRule] = {}
        self._active_rules: List[ISocialRule] = []
        self._active_rule_names: List[str] = active_rules if active_rules else [".*"]

        if rules:
            for rule in rules:
                self.add(rule)

    def add(self, rule: ISocialRule) -> None:
        """
        Add a rule to the library

        Parameters
        ----------
        rule: ISocialRule
            The rule to add
        """
        self._all_rules[rule.get_uid()] = rule
        if any(
            [re.match(pattern, rule.get_uid()) for pattern in self._active_rule_names]
        ):
            self._active_rules.append(rule)

    def set_active_rules(self, rule_names: List[str]) -> None:
        """
        Sets the rules with names that match the regex strings as active

        Parameters
        ----------
        rule_names: List[str]
            Regex strings for rule names to activate
        """
        self._active_rules.clear()
        self._active_rule_names = rule_names
        for name, rule in self._all_rules.items():
            if any([re.match(pattern, name) for pattern in self._active_rule_names]):
                self._active_rules.append(rule)

    def get_active_rules(self) -> List[ISocialRule]:
        """Return social rules that are active for relationship calculations"""
        return self._active_rules
