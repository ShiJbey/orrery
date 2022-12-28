import re
from typing import Dict, List, Optional, Protocol

from orrery.core.ecs import GameObject, World
from orrery.core.relationship import IRelationshipModifier, Relationship


class ISocialRule(Protocol):
    """Social rules combine preconditions with modifiers"""

    def get_uid(self) -> str:
        """Return the unique identifier of the modifier"""
        raise NotImplementedError

    def check_preconditions(self, world: World, *gameobjects: GameObject) -> bool:
        """Return true if a certain condition holds"""
        raise NotImplementedError

    def activate(
        self,
        world: World,
        subject: GameObject,
        target: GameObject,
        relationship: Relationship,
    ) -> None:
        """Apply any modifiers associated with the social rule"""
        raise NotImplementedError

    def deactivate(self, relationship: Relationship) -> None:
        """Apply any modifiers associated with the social rule"""
        raise NotImplementedError


class ISocialRulePrecondition(Protocol):
    """Callable that checks if a condition is true between gameobjects"""

    def __call__(self, world: World, *gameobjects: GameObject) -> bool:
        raise NotImplementedError


class SocialRule:
    """Simple implementation of social rules"""

    __slots__ = "precondition", "modifiers", "name"

    def __init__(
        self,
        name: str,
        precondition: ISocialRulePrecondition,
        modifiers: List[IRelationshipModifier],
    ) -> None:
        self.name: str = name
        self.precondition: ISocialRulePrecondition = precondition
        self.modifiers: List[IRelationshipModifier] = modifiers

    def get_uid(self) -> str:
        """Return the unique identifier of the modifier"""
        return self.name

    def check_preconditions(self, world: World, *gameobjects: GameObject) -> bool:
        """Return true if a certain condition holds"""
        return self.precondition(world, *gameobjects)

    def activate(
        self,
        world: World,
        subject: GameObject,
        target: GameObject,
        relationship: Relationship,
    ) -> None:
        """Apply any modifiers associated with the social rule"""
        for modifier in self.modifiers:
            relationship.add_modifier(modifier)
            modifier.activate(relationship)

    def deactivate(self, relationship: Relationship) -> None:
        """Apply any modifiers associated with the social rule"""
        for modifier in self.modifiers:
            if modifier.get_uid() in relationship.active_modifiers:
                relationship.remove_modifier(modifier)
                modifier.deactivate(relationship)


class SocialRuleLibrary:
    """
    Library of compatibility rules that affect
    how characters feel about each other.
    """

    __slots__ = "_library", "_active_rules", "_active_rule_regex"

    def __init__(
        self,
        rules: Optional[List[ISocialRule]] = None,
        active_rules: Optional[List[str]] = None,
    ) -> None:
        self._library: Dict[str, ISocialRule] = {}
        self._active_rules: List[ISocialRule] = []
        self._active_rule_regex: List[str] = active_rules if active_rules else [".*"]

        if rules:
            for r in rules:
                self._library[r.get_uid()] = r
                if any(
                    [
                        re.match(pattern, r.get_uid())
                        for pattern in self._active_rule_regex
                    ]
                ):
                    self._active_rules.append(r)

    def add(self, rule: ISocialRule) -> None:
        """Add a rule to the library"""
        self._library[rule.get_uid()] = rule

    def set_active_rules(self, rule_names: List[str]) -> None:
        """Sets the rules with the given regex names as active during relationship calculations"""
        self._active_rules.clear()
        self._active_rule_regex = rule_names
        for name, rule in self._library.items():
            if any([re.match(pattern, name) for pattern in self._active_rule_regex]):
                self._active_rules.append(rule)

    def get_active_rules(self) -> List[ISocialRule]:
        """Return social rules that are active for relationship calculations"""
        return self._active_rules
