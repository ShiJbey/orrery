from __future__ import annotations

import math
from dataclasses import dataclass
from enum import IntFlag, auto
from typing import Any, Dict, Iterator, List, Protocol, Tuple, Type

from orrery.core.ecs import Component, ISystem


def lerp(a: float, b: float, f: float) -> float:
    return (a * (1.0 - f)) + (b * f)


class RelationshipStatNotfound(Exception):
    """Exception raised when trying to access a relationship stat that does not exist"""

    __slots__ = "name"

    def __init__(self, name: str) -> None:
        super(Exception, self).__init__(name)
        self.name: str = name

    def __str__(self) -> str:
        return f"Could not find relationship with name ({self.name}). Check your schema config"


class RelationshipNotFound(Exception):
    """Exception raised when trying to access a relationship that does not exist"""

    __slots__ = "subject", "target"

    def __init__(self, subject: str, target: str) -> None:
        super(Exception, self).__init__(target)
        self.target: str = target
        self.subject: str = subject

    def __str__(self) -> str:
        return (
            f"Could not find relationship between ({self.subject}) and ({self.target})"
        )


class IncrementTuple:
    def __init__(self, value: Tuple[int, int] = (0, 0)) -> None:
        self._value: Tuple[int, int] = value

        if self._value[0] < 0 or self._value[1] < 0:
            raise ValueError("Values of an IncrementTuple may not be less than zero.")

    @property
    def increments(self) -> int:
        """Return the number of increments"""
        return self._value[0]

    @property
    def decrements(self) -> int:
        """Return the number of decrements"""
        return self._value[1]

    def __iadd__(self, value: int) -> IncrementTuple:
        """Overrides += operator for relationship stats"""
        if value > 0:
            self._value = (self._value[0] + value, self._value[1])
        if value < 0:
            self._value = (self._value[0], self._value[1] + abs(value))
        return self

    def __add__(self, other: IncrementTuple) -> IncrementTuple:
        return IncrementTuple(
            (self.increments + other.increments, self.decrements + other.decrements)
        )


class RelationshipStat:
    """
    A scalar value quantifying a relationship from one entity to another

    Attributes
    ----------
    _min_value: int
        The minimum scaled value this stat can hold
    _max_value: int
        The maximum scaled value this stat can hold
    _raw_value: int
        The current raw score for this stat
    _scaled_value: int
        Scales the normalized score between the minimum and maximum
    _normalized_value: float
        The  normalized stat value on the interval [0.0, 1.0]
    _is_dirty: bool
        Have the various values been recalculated since the last change
    """

    __slots__ = (
        "_min_value",
        "_max_value",
        "_raw_value",
        "_scaled_value",
        "_normalized_value",
        "_base",
        "_from_modifiers",
        "_is_dirty",
        "changes_with_time",
    )

    def __init__(self, min_value: int, max_value: int, changes_with_time: bool) -> None:
        self._min_value: int = min_value
        self._max_value: int = max_value
        self._raw_value: int = 0
        self._scaled_value: int = 0
        self._normalized_value: float = 0.5
        self._base: IncrementTuple = IncrementTuple()
        self._from_modifiers: IncrementTuple = IncrementTuple()
        self._is_dirty: bool = False
        self.changes_with_time: bool = changes_with_time

    def get_base(self) -> IncrementTuple:
        """Return the base value for increments on this relationship stat"""
        return self._base

    def set_base(self, value: Tuple[int, int]) -> None:
        """Set the base value for decrements on this relationship stat"""
        self._base = IncrementTuple(value)

    def add_modifier(self, value: int) -> None:
        self._from_modifiers += value
        self._is_dirty = True

    def remove_modifier(self, value: int) -> None:
        self._from_modifiers += -value
        self._is_dirty = True

    def get_raw_value(self) -> int:
        """Return the raw value of this relationship stat"""
        if self._is_dirty:
            self._recalculate_values()
        return self._raw_value

    def get_scaled_value(self) -> int:
        """Return the scaled value of this relationship stat between the max and min values"""
        if self._is_dirty:
            self._recalculate_values()
        return self._scaled_value

    def get_normalized_value(self) -> float:
        """Return the normalized value of this relationship stat on the interval [0.0, 1.0]"""
        if self._is_dirty:
            self._recalculate_values()
        return self._normalized_value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw": self.get_raw_value(),
            "scaled": self.get_scaled_value(),
            "normalized": self.get_normalized_value(),
        }

    def _recalculate_values(self) -> None:
        """Recalculate the various values since the last change"""
        combined_increments = self._base + self._from_modifiers

        self._raw_value = (
            combined_increments.increments - combined_increments.decrements
        )

        total_changes = combined_increments.increments + combined_increments.decrements

        if total_changes == 0:
            self._normalized_value = 0.5
        else:
            self._normalized_value = (
                float(combined_increments.increments) / total_changes
            )

        self._scaled_value = math.ceil(
            lerp(self._min_value, self._max_value, self._normalized_value)
        )

        self._is_dirty = False

    def __iadd__(self, value: int) -> RelationshipStat:
        """Overrides += operator for relationship stats"""
        self._base += value
        self._is_dirty = True
        return self

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return "RelationshipStat(norm={}, raw={}, scaled={},  max={}, min={})".format(
            self.get_normalized_value(),
            self.get_raw_value(),
            self.get_scaled_value(),
            self._max_value,
            self._min_value,
        )


@dataclass(frozen=True)
class SimpleRelationshipModifier:

    uid: str
    modifiers: Dict[str, int]

    def get_uid(self) -> str:
        """Return the unique identifier of the modifier"""
        return self.uid

    def get_description(self) -> str:
        """Return a text description of the modifier"""
        return str(self.to_dict())

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the modifier to a dictionary"""
        return {"uid": self.uid, "modifiers": {**self.modifiers}}

    def activate(self, relationship: Relationship) -> None:
        """Apply this modifier to the given relationship"""
        for stat, buff in self.modifiers.items():
            relationship[stat].add_modifier(buff)

    def deactivate(self, relationship: Relationship) -> None:
        """Remove this modifier's effects from the given relationship"""
        for stat, buff in self.modifiers.items():
            relationship[stat].remove_modifier(buff)


class RelationshipTag(IntFlag):
    Empty = auto()
    Family = auto()
    Parent = auto()
    Child = auto()
    Sibling = auto()
    Coworker = auto()
    SignificantOther = auto()
    Spouse = auto()
    Friend = auto()
    Enemy = auto()
    Dating = auto()
    Married = auto()


class Relationship:

    __slots__ = (
        "_stats",
        "interaction_score",
        "tags",
        "active_modifiers",
        "_is_dirty",
        "target",
        "statuses",
    )

    def __init__(self, target: int, stats: Dict[str, RelationshipStat]) -> None:
        self.target: int = target
        self.interaction_score: RelationshipStat = RelationshipStat(-5, 5, False)
        self._stats: Dict[str, RelationshipStat] = {
            **stats,
            "Interaction": self.interaction_score,
        }
        self.tags: RelationshipTag = RelationshipTag.Empty
        self.statuses: Dict[Type[Component], int] = {}
        self.active_modifiers: Dict[str, IRelationshipModifier] = {}
        self._is_dirty = False

    def add_status(self, status_id: int, status_type: Type[Component]) -> None:
        """
        Add a relationship status to this relationship

        Parameters
        ----------
        status_id: int
            The ID of the GameObject with the status information
        status_type: Type[Component]
            The main component associated with the status
        """
        self.statuses[status_type] = status_id

    def get_status(self, status_type: Type[Component]) -> int:
        """
        Get the ID of the status with this component type

        Parameters
        ----------
        status_type: Type[Component]
            The main component associated with the status
        """
        return self.statuses[status_type]

    def remove_status(self, status_type: Type[Component]) -> None:
        """
        Remove a relationship status from this relationship

        Parameters
        ----------
        status_type: Type[Component]
            The main component associated with the status
        """
        del self.statuses[status_type]

    def has_status(self, status_type: Type[Component]) -> bool:
        """
        Remove a relationship status from this relationship

        Parameters
        ----------
        status_type: Type[Component]
            The mani component associated with the status
        """
        return status_type in self.statuses.values()

    def add_tags(self, tags: RelationshipTag) -> None:
        self.tags |= tags

    def remove_tags(self, tags: RelationshipTag) -> None:
        self.tags ^= tags

    def add_modifier(self, modifier: IRelationshipModifier) -> None:
        self.active_modifiers[modifier.get_uid()] = modifier
        modifier.activate(self)

    def remove_modifier(self, modifier: IRelationshipModifier) -> None:
        del self.active_modifiers[modifier.get_uid()]
        modifier.deactivate(self)

    def remove_modifier_by_uid(self, uid: str) -> None:
        modifier = self.active_modifiers[uid]
        modifier.deactivate(self)
        del self.active_modifiers[uid]

    def __getitem__(self, item: str) -> RelationshipStat:
        try:
            return self._stats[item]
        except KeyError:
            raise RelationshipStatNotfound(item)

    def __setitem__(self, item: str, value: RelationshipStat) -> RelationshipStat:
        # This function is here to allow user to do (+=) in combination with [] syntax
        # for example: relationship["Friendship"] += 3
        # It's a slight abuse of syntax, but it works
        return self._stats[item]

    def __iter__(self) -> Iterator[tuple[str, RelationshipStat]]:
        return self._stats.items().__iter__()

    def to_dict(self) -> Dict[str, Any]:
        return {
            **{k: stat.to_dict() for k, stat in self._stats.items()},
            "tags": str(self.tags),
            "active_modifiers": [m.to_dict() for _, m in self.active_modifiers.items()],
        }


class RelationshipManager(Component):

    __slots__ = "_relationships"

    def __init__(self) -> None:
        super(Component, self).__init__()
        self._relationships: Dict[int, Relationship] = {}

    def add(self, target: int, relationship: Relationship) -> None:
        """Adds a new entity to the relationship manager and returns the new relationship between the two"""
        self._relationships[target] = relationship

    def get(self, target: int) -> Relationship:
        """
        Get a relationship toward another entity

        Parameters
        ----------
        target: int
            Unique identifier of the other entity

        Returns
        -------
        Relationship
            The relationship instance toward the other entity

        Throws
        ------
        KeyError
            If no relationship is found for the given target and create_new is False
        """
        return self._relationships[target]

    def get_all_with_tags(self, tags: RelationshipTag) -> List[Relationship]:
        """
        Get all the relationships between a character and others with specific tags
        """
        return [rel for _, rel in self._relationships.items() if tags in rel.tags]

    def to_dict(self) -> Dict[str, Any]:
        return {str(t): r.to_dict() for t, r in self._relationships.items()}

    def __iter__(self) -> Iterator[tuple[int, Relationship]]:
        return self._relationships.items().__iter__()

    def __contains__(self, target: int) -> bool:
        """Returns True if there is a relationship to the target"""
        return target in self._relationships


class IRelationshipModifier(Protocol):
    """Modifies the stat values of a relationship"""

    def get_uid(self) -> str:
        """Return the unique identifier of the modifier"""
        raise NotImplementedError

    def get_description(self) -> str:
        """Return a text description of the modifier"""
        raise NotImplementedError

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the modifier to a dictionary"""
        raise NotImplementedError

    def activate(self, relationship: Relationship) -> None:
        """Apply this modifier to the given relationship"""
        raise NotImplementedError

    def deactivate(self, relationship: Relationship) -> None:
        """Remove this modifier's effects from the given relationship"""
        raise NotImplementedError


class RelationshipModifier:
    def __init__(self, uid: str, modifiers: Dict[str, int]) -> None:
        self.uid: str = uid
        self.modifiers: Dict[str, int] = modifiers

    def get_uid(self) -> str:
        """Return the unique identifier of the modifier"""
        return self.uid

    def get_description(self) -> str:
        """Return a text description of the modifier"""
        return str(self.modifiers)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the modifier to a dictionary"""
        return {"uid": self.uid, "modifiers": self.modifiers}

    def activate(self, relationship: Relationship) -> None:
        """Apply this modifier to the given relationship"""
        for stat, buff in self.modifiers.items():
            relationship[stat].add_modifier(buff)

    def deactivate(self, relationship: Relationship) -> None:
        """Remove this modifier's effects from the given relationship"""
        for stat, buff in self.modifiers.items():
            relationship[stat].remove_modifier(-buff)


class UpdateRelationshipsSystem(ISystem):
    """Updates the relationship stats between characters using their interaction scores"""

    def process(self, *args: Any, **kwargs: Any) -> None:
        for _, manager in self.world.get_component(RelationshipManager):
            for _, relationship in manager:
                for _, stat in relationship:
                    if stat.changes_with_time:
                        stat += round(
                            max(0, relationship.interaction_score.get_raw_value())
                            * lerp(-3, 3, stat.get_normalized_value())
                        )
