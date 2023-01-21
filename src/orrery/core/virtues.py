"""
virtues.py

Virtues are the most basic way that character personalities are represented.
They are used in the simulation to determine how compatible characters are,
thus affecting how their relationship will evolve over time. Virtues may also
be used to determine how likely a character is to engage in a given event/action.
"""
from __future__ import annotations

import enum
import logging
import random
from typing import Any, Dict, Iterator, List, Optional, Tuple

import numpy as np
import numpy.typing as npt

from orrery.core.ecs import Component, IComponentFactory, World

logger = logging.getLogger(__name__)


class VirtueType(enum.IntEnum):
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
        super(Component, self).__init__()
        self._virtues: npt.NDArray[np.int32] = np.zeros(  # type: ignore
            len(VirtueType), dtype=np.int32
        )

        if overrides:
            for trait, value in overrides.items():
                self[VirtueType[trait]] = value

    def to_array(self) -> npt.NDArray[np.int32]:
        """Converts the virtue"""
        return self._virtues

    def compatibility(self, other: Virtues) -> float:
        """
        Calculates the cosine similarity between one VirtueVector and an other

        Parameters
        ----------
        other : Virtues
            The other set of virtues to compare to

        Returns
        -------
        float
            Similarity score on the range [-1.0, 1.0]
        """
        # Cosine similarity is a value between -1 and 1
        norm_product: float = float(
            np.linalg.norm(self.to_array()) * np.linalg.norm(other.to_array())  # type: ignore
        )

        if norm_product == 0:
            return 0
        else:
            return round(
                float(np.dot(self.to_array(), other.to_array()) / norm_product), 2  # type: ignore
            )

    def get_high_values(self, n: int = 3) -> List[VirtueType]:
        """Return the virtues names associated with the n-highest values"""
        sorted_index_array = np.argsort(self.to_array())[-n:]  # type: ignore

        value_names = list(VirtueType)

        return [value_names[i] for i in sorted_index_array]

    def get_low_values(self, n: int = 3) -> List[VirtueType]:
        """Return the virtues names associated with the n-lowest values"""
        sorted_index_array = np.argsort(self.to_array())[:n]  # type: ignore

        value_names = list(VirtueType)

        return [value_names[i] for i in sorted_index_array]

    def __getitem__(self, item: int) -> int:
        return int(self._virtues[item])

    def __setitem__(self, item: int, value: int) -> None:
        self._virtues[item] = max(Virtues.VIRTUE_MIN, min(Virtues.VIRTUE_MAX, value))

    def __str__(self) -> str:
        return str(self.to_dict())

    def __repr__(self) -> str:
        return "{}({})".format(self.__class__.__name__, self._virtues.__repr__())

    def __iter__(self) -> Iterator[Tuple[VirtueType, int]]:
        virtue_dict = {
            virtue: int(self._virtues[i]) for i, virtue in enumerate(list(VirtueType))
        }

        return virtue_dict.items().__iter__()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "virtues": {
                virtue.name: int(self._virtues[i])
                for i, virtue in enumerate(list(VirtueType))
            },
        }


class VirtuesFactory(IComponentFactory):
    def create(
        self,
        world: World,
        n_likes: int = 3,
        n_dislikes: int = 3,
        initialization: str = "zeros",
        overrides: Optional[Dict[str, int]] = None,
        **kwargs: Any,
    ) -> Component:
        """Generate a new set of character values"""
        values_overrides: Dict[str, int] = {}

        if initialization == "zeros":
            pass

        elif initialization == "random":
            rng = world.get_resource(random.Random)

            # Select virtues types
            total_virtues: int = n_likes + n_dislikes
            chosen_virtues = [
                virtue.name for virtue in rng.sample(list(VirtueType), total_virtues)
            ]

            # select likes and dislikes
            high_values = rng.sample(chosen_virtues, n_likes)
            low_values = list(set(chosen_virtues) - set(high_values))

            # Generate values for each ([30,50] for high values, [-50,-30] for dislikes)
            for trait in high_values:
                values_overrides[trait] = rng.randint(30, 50)

            for trait in low_values:
                values_overrides[trait] = rng.randint(-50, -30)
        else:
            # Using an unknown virtue doesn't break anything, but we should log it
            logger.warning(f"Unrecognized Virtues initialization '{initialization}'")

        if overrides is not None:
            # Override any values with manually-specified values
            values_overrides = {**values_overrides, **overrides}

        return Virtues(values_overrides)
