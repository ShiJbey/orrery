from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Iterator, List, Tuple

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

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return "{}(increments={}, decrements={})".format(
            self.__class__.__name__, self.increments, self.decrements
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
    _clamped_value: int
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
        "_clamped_value",
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
        self._clamped_value: int = 0
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

    def get_value(self) -> int:
        """Return the scaled value of this relationship stat between the max and min values"""
        if self._is_dirty:
            self._recalculate_values()
        return self._clamped_value

    def get_normalized_value(self) -> float:
        """Return the normalized value of this relationship stat on the interval [0.0, 1.0]"""
        if self._is_dirty:
            self._recalculate_values()
        return self._normalized_value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw": self.get_raw_value(),
            "scaled": self.get_value(),
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

        self._clamped_value = math.ceil(
            max(self._min_value, min(self._max_value, self._raw_value))
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
        return "{}(value={}, norm={}, raw={},  max={}, min={})".format(
            self.__class__.__name__,
            self.get_value(),
            self.get_normalized_value(),
            self.get_raw_value(),
            self._max_value,
            self._min_value,
        )


@dataclass
class RelationshipModifier:

    name: str
    values: Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "values": {**self.values}}


class Relationship(Component):

    __slots__ = (
        "_stats",
        "interaction_score",
        "modifiers",
        "_is_dirty",
        "target",
        "owner",
    )

    def __init__(
        self, owner: int, target: int, stats: Dict[str, RelationshipStat]
    ) -> None:
        super().__init__()
        self.owner: int = owner
        self.target: int = target
        self.interaction_score: RelationshipStat = RelationshipStat(-5, 5, False)
        self._stats: Dict[str, RelationshipStat] = {
            **stats,
            "Interaction": self.interaction_score,
        }
        self.modifiers: List[RelationshipModifier] = []
        self._is_dirty = False

    def add_modifier(self, modifier: RelationshipModifier) -> None:
        self.modifiers.append(modifier)

        for stat_name, value in modifier.values.items():
            self[stat_name].add_modifier(value)

    def clear_modifiers(self) -> None:
        for modifier in self.modifiers:
            for stat_name, value in modifier.values.items():
                self[stat_name].remove_modifier(value)
        self.modifiers.clear()

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
            "owner": self.owner,
            "target": self.target,
            **{k: stat.to_dict() for k, stat in self._stats.items()},
            "modifiers": [m.to_dict() for m in self.modifiers],
        }

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return "{}(owner={}, target={}, stats={}, modifiers={})".format(
            self.__class__.__name__,
            self.owner,
            self.target,
            self._stats,
            self.modifiers,
        )


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
        return {str(k): v for k, v in self.relationships.items()}

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return "{}({})".format(self.__class__.__name__, self.relationships)
