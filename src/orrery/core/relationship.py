from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Iterator, Protocol, Tuple, TypeVar

from orrery.core.ecs import Component


def lerp(a: float, b: float, f: float) -> float:
    return (a * (1.0 - f)) + (b * f)


class RelationshipStatNotfound(Exception):
    """Exception raised when trying to access a relationship stat that does not exist"""

    __slots__ = "name", "message"

    def __init__(self, name: str) -> None:
        super(Exception, self).__init__(name)
        self.name: str = name
        self.message: str = f"Could not find relationship with name ({self.name}). Check your schema config"

    def __str__(self) -> str:
        return self.message

    def __repr__(self) -> str:
        return "{}(name={})".format(self.__class__.__name__, self.name)


class RelationshipNotFound(Exception):
    """Exception raised when trying to access a relationship that does not exist"""

    __slots__ = "subject", "target", "message"

    def __init__(self, subject: str, target: str) -> None:
        super(Exception, self).__init__(target)
        self.subject: str = subject
        self.target: str = target
        self.message: str = (
            f"Could not find relationship between ({self.subject}) and ({self.target})"
        )

    def __str__(self) -> str:
        return self.message

    def __repr__(self) -> str:
        return "{}(subject={}, target={})".format(
            self.__class__.__name__, self.subject, self.target
        )


class IncrementCounter:
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

    def __iadd__(self, value: int) -> IncrementCounter:
        """Overrides += operator for relationship stats"""
        if value > 0:
            self._value = (self._value[0] + value, self._value[1])
        if value < 0:
            self._value = (self._value[0], self._value[1] + abs(value))
        return self

    def __add__(self, other: IncrementCounter) -> IncrementCounter:
        return IncrementCounter(
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
        self._base: IncrementCounter = IncrementCounter()
        self._from_modifiers: IncrementCounter = IncrementCounter()
        self._is_dirty: bool = False
        self.changes_with_time: bool = changes_with_time

    def get_base(self) -> IncrementCounter:
        """Return the base value for increments on this relationship stat"""
        return self._base

    def set_base(self, value: Tuple[int, int]) -> None:
        """Set the base value for decrements on this relationship stat"""
        self._base = IncrementCounter(value)

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


_RST = TypeVar("_RST", bound="RelationshipStatus")


class Relationship(Component):

    __slots__ = (
        "_stats",
        "interaction_score",
        "active_modifiers",
        "_is_dirty",
        "target",
    )

    def __init__(self, target: int, stats: Dict[str, RelationshipStat]) -> None:
        super().__init__()
        self.target: int = target
        self.interaction_score: RelationshipStat = RelationshipStat(-5, 5, False)
        self._stats: Dict[str, RelationshipStat] = {
            **stats,
            "Interaction": self.interaction_score,
        }
        self.active_modifiers: Dict[str, IRelationshipModifier] = {}
        self._is_dirty = False

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
        self._is_dirty = True
        return self._stats[item]

    def __iter__(self) -> Iterator[tuple[str, RelationshipStat]]:
        return self._stats.items().__iter__()

    def to_dict(self) -> Dict[str, Any]:
        return {
            **{k: stat.to_dict() for k, stat in self._stats.items()},
            "active_modifiers": [m.to_dict() for _, m in self.active_modifiers.items()],
        }


class RelationshipManager(Component):
    """Tracks all relationships associated with a GameObject

    Attributes
    ----------
    relationships: Dict[int, int]
        GameObject ID of relationship targets mapped to the ID of the
        GameObjects with the relationship data
    """

    __slots__ = "relationships"

    def __init__(self) -> None:
        super().__init__()
        self.relationships: Dict[int, int] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {**self.relationships}


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
