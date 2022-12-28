from __future__ import annotations

import enum
import random
from typing import Any, Dict, List

import numpy as np
import numpy.typing as npt

from orrery.core.ecs import Component, IComponentFactory, Optional, World


class Virtue(enum.Enum):
    ADVENTURE = "adventure"
    AMBITION = "ambition"
    EXCITEMENT = "excitement"
    COMMERCE = "commerce"
    CONFIDENCE = "confidence"
    CURIOSITY = "curiosity"
    FAMILY = "family"
    FRIENDSHIP = "friendship"
    WEALTH = "wealth"
    HEALTH = "health"
    INDEPENDENCE = "independence"
    KNOWLEDGE = "knowledge"
    LEISURE_TIME = "leisure-time"
    LOYALTY = "loyalty"
    LUST = "lust"
    MATERIAL_THINGS = "material things"
    NATURE = "nature"
    PEACE = "peace"
    POWER = "power"
    RELIABILITY = "reliability"
    ROMANCE = "romance"
    SINGLE_MINDEDNESS = "single mindedness"
    SOCIALIZING = "socializing"
    SELF_CONTROL = "self-control"
    TRADITION = "tradition"
    TRANQUILITY = "tranquility"


_VIRTUE_UIDS: Dict[str, int] = {
    str(virtue.value): index for index, virtue in enumerate(Virtue)
}


class VirtueVector(Component):
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

    def __init__(
        self, overrides: Optional[Dict[str, int]] = None, default: int = 0
    ) -> None:
        super().__init__()
        self._virtues: npt.NDArray[np.int32] = np.array(  # type: ignore
            [default] * len(_VIRTUE_UIDS.keys()), dtype=np.int32
        )

        if overrides:
            for trait, value in overrides.items():
                self._virtues[_VIRTUE_UIDS[trait]] = max(
                    self.VIRTUE_MIN, min(self.VIRTUE_MAX, value)
                )

    @property
    def virtues(self) -> npt.NDArray[np.int32]:
        return self._virtues

    def compatibility(self, other: VirtueVector) -> float:
        """
        Calculates the cosine similarity between one VirtueVector and an other

        Parameters
        ----------
        other : VirtueVector
            The other set of virtues to compare to

        Returns
        -------
        float
            Similarity score on the range [-1.0, 1.0]
        """
        # Cosine similarity is a value between -1 and 1
        norm_product: float = np.linalg.norm(self.virtues) * np.linalg.norm(other.virtues)  # type: ignore

        if norm_product == 0:
            return 0
        else:
            return np.dot(self.virtues, other.virtues) / norm_product  # type: ignore

    def get_high_values(self, n: int = 3) -> List[str]:
        """Return the virtues names associated with the n values"""
        # This code is adapted from https://stackoverflow.com/a/23734295

        ind = np.argpartition(self.virtues, -n)[-n:]  # type: ignore

        value_names = list(_VIRTUE_UIDS.keys())

        return [value_names[i] for i in ind]

    def __getitem__(self, virtue: str) -> int:
        return self._virtues[_VIRTUE_UIDS[virtue]]  # type: ignore

    def __setitem__(self, virtue: str, value: int) -> None:
        self._virtues[_VIRTUE_UIDS[virtue]] = max(
            VirtueVector.VIRTUE_MIN, min(VirtueVector.VIRTUE_MAX, value)
        )

    def __str__(self) -> str:
        return f"Values Most: {self.get_high_values()}"

    def __repr__(self) -> str:
        return "{}({})".format(self.__class__.__name__, self._virtues.__repr__())

    def to_dict(self) -> Dict[str, Any]:
        return {
            **super().to_dict(),
            **{
                virtue.name: int(self._virtues[i])
                for i, virtue in enumerate(list(Virtue))
            },
        }


class VirtueVectorFactory(IComponentFactory):
    def create(
        self, world: World, n_likes: int = 3, n_dislikes: int = 3, **kwargs: Any
    ) -> Component:
        """Generate a new set of character values"""
        rng = world.get_resource(random.Random)

        # Select Traits
        total_virtues: int = n_likes + n_dislikes
        chosen_virtues = [
            str(virtue.value) for virtue in rng.sample(list(Virtue), total_virtues)
        ]

        # select likes and dislikes
        high_values = rng.sample(chosen_virtues, n_likes)
        low_values = list(set(chosen_virtues) - set(high_values))

        # Generate values for each ([30,50] for high values, [-50,-30] for dislikes)
        values_overrides: Dict[str, int] = {}

        for trait in high_values:
            values_overrides[trait] = rng.randint(30, 50)

        for trait in low_values:
            values_overrides[trait] = rng.randint(-50, -30)

        return VirtueVector(values_overrides)
