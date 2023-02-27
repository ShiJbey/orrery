"""
virtues.py

Virtues are a built-in personality representation.

They are used in the simulation to determine how compatible characters are,
thus affecting how their relationship will evolve over time. Virtues may also
be used to determine how likely a character is to engage in a given event/action.
"""
from __future__ import annotations

import enum
from typing import Any, Dict, Iterator, List, Optional, Tuple

import numpy as np
import numpy.typing as npt

from orrery.core.ecs import Component


class Virtue(enum.IntEnum):
    ADVENTURE = 0
    AMBITION = enum.auto()
    EXCITEMENT = enum.auto()
    COMMERCE = enum.auto()
    CONFIDENCE = enum.auto()
    CURIOSITY = enum.auto()
    FAMILY = enum.auto()
    FRIENDSHIP = enum.auto()
    WEALTH = enum.auto()
    HEALTH = enum.auto()
    INDEPENDENCE = enum.auto()
    KNOWLEDGE = enum.auto()
    LEISURE_TIME = enum.auto()
    LOYALTY = enum.auto()
    LUST = enum.auto()
    MATERIAL_THINGS = enum.auto()
    NATURE = enum.auto()
    PEACE = enum.auto()
    POWER = enum.auto()
    RELIABILITY = enum.auto()
    ROMANCE = enum.auto()
    SINGLE_MINDEDNESS = enum.auto()
    SOCIALIZING = enum.auto()
    SELF_CONTROL = enum.auto()
    TRADITION = enum.auto()
    TRANQUILITY = enum.auto()


class Virtues(Component):
    """
    Values are what an entity believes in. They are used
    for decision-making and relationship compatibility among
    other things.


    Individual values are integers on the range [-50,50], inclusive.

    This model of entity values is borrowed from Dwarf Fortress'
    model of entity beliefs/values outlined at the following link
    https://dwarffortresswiki.org/index.php/DF2014:Personality_trait
    """

    VIRTUE_MAX = 50
    VIRTUE_MIN = -50

    __slots__ = "_virtues"

    def __init__(self, overrides: Optional[Dict[str, int]] = None) -> None:
        super().__init__()
        self._virtues: npt.NDArray[np.int32] = np.zeros(  # type: ignore
            len(Virtue), dtype=np.int32
        )

        if overrides:
            for trait, value in overrides.items():
                self[Virtue[trait]] = value

    def compatibility(self, other: Virtues) -> int:
        """Calculates the similarity between two Virtue components

        Parameters
        ----------
        other : Virtues
            The other set of virtues to compare to

        Returns
        -------
        int
            Similarity score on the range [-100, 100]
        """
        # Cosine similarity is a value between -1 and 1
        norm_product: float = float(
            np.linalg.norm(self._virtues) * np.linalg.norm(other._virtues)  # type: ignore
        )

        if norm_product == 0:
            cosine_similarity = 0.0
        else:
            cosine_similarity = float(np.dot(self._virtues, other._virtues) / norm_product)  # type: ignore

        # Distance similarity is a value between -1 and 1
        max_distance = 509.9019513592785
        distance = float(np.linalg.norm(self._virtues - other._virtues)) # type: ignore
        distance_similarity = 2.0 * (1.0 - (distance / max_distance)) - 1.0

        similarity: int = round(100 * ((cosine_similarity + distance_similarity) / 2.0))

        return similarity

    def get_high_values(self, n: int = 3) -> List[Virtue]:
        """Return the virtues names associated with the n-highest values"""
        sorted_index_array = np.argsort(self._virtues)[-n:]  # type: ignore

        value_names = list(Virtue)

        return [value_names[i] for i in sorted_index_array]

    def get_low_values(self, n: int = 3) -> List[Virtue]:
        """Return the virtues names associated with the n-lowest values"""
        sorted_index_array = np.argsort(self._virtues)[:n]  # type: ignore

        value_names = list(Virtue)

        return [value_names[i] for i in sorted_index_array]

    def __getitem__(self, item: int) -> int:
        return int(self._virtues[item])

    def __setitem__(self, item: int, value: int) -> None:
        self._virtues[item] = max(Virtues.VIRTUE_MIN, min(Virtues.VIRTUE_MAX, value))

    def __str__(self) -> str:
        return str(self.to_dict())

    def __repr__(self) -> str:
        return "{}({})".format(self.__class__.__name__, self._virtues.__repr__())

    def __iter__(self) -> Iterator[Tuple[Virtue, int]]:
        virtue_dict = {
            virtue: int(self._virtues[i]) for i, virtue in enumerate(list(Virtue))
        }

        return virtue_dict.items().__iter__()

    def to_dict(self) -> Dict[str, Any]:
        return {
            **{
                virtue.name: int(self._virtues[i])
                for i, virtue in enumerate(list(Virtue))
            },
        }
