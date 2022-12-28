from __future__ import annotations

import random
from typing import Any, Dict, List, Optional

from ordered_set import OrderedSet
from orrery.core.config import ResidenceConfig  # type: ignore

from orrery.core.ecs import Component


class Residence(Component):
    """Residence is a place where characters live"""

    __slots__ = "owners", "former_owners", "residents", "former_residents", "_vacant"

    def __init__(self) -> None:
        super(Component, self).__init__()
        self.owners: OrderedSet[int] = OrderedSet([])
        self.former_owners: OrderedSet[int] = OrderedSet([])
        self.residents: OrderedSet[int] = OrderedSet([])
        self.former_residents: OrderedSet[int] = OrderedSet([])

    def to_dict(self) -> Dict[str, Any]:
        return {
            **super().to_dict(),
            "owners": list(self.owners),
            "former_owners": list(self.former_owners),
            "residents": list(self.residents),
            "former_residents": list(self.former_residents),
        }

    def add_owner(self, owner: int) -> None:
        """Add owner to the residence"""
        self.owners.add(owner)

    def remove_owner(self, owner: int) -> None:
        """Remove owner from residence"""
        self.owners.remove(owner)

    def is_owner(self, character: int) -> bool:
        """Return True if the entity is an owner of this residence"""
        return character in self.owners

    def add_resident(self, resident: int) -> None:
        """Add a tenant to this residence"""
        self.residents.add(resident)

    def remove_resident(self, resident: int) -> None:
        """Remove a tenant rom this residence"""
        self.residents.remove(resident)
        self.former_residents.add(resident)

    def is_resident(self, character: int) -> bool:
        """Return True if the given entity is a resident"""
        return character in self.residents


class Resident(Component):
    """Component attached to characters indicating that they live in the town"""

    __slots__ = "residence"

    def __init__(self, residence: int) -> None:
        super().__init__()
        self.residence: int = residence

    def to_dict(self) -> Dict[str, Any]:
        return {**super().to_dict(), "residence": self.residence}


class Vacant(Component):
    """Tags a residence that does not currently have anyone living there"""

    pass


class ResidenceLibrary:
    """Collection factories that create residence entities"""

    __slots__ = "_registry"

    def __init__(self) -> None:
        self._registry: Dict[str, ResidenceConfig] = {}

    def add(
        self,
        config: ResidenceConfig,
    ) -> None:
        """Register a new archetype by name"""
        self._registry[config.name] = config

    def get_all(self) -> List[ResidenceConfig]:
        """Get all stored archetypes"""
        return list(self._registry.values())

    def get(self, name: str) -> ResidenceConfig:
        """Get an archetype by name"""
        return self._registry[name]

    def choose_random(self, rng: random.Random) -> Optional[ResidenceConfig]:
        choices: List[ResidenceConfig] = []
        weights: List[int] = []
        for archetype in self.get_all():
            choices.append(archetype)
            weights.append(archetype.spawning.spawn_frequency)

        if choices:
            # Choose an archetype at random
            archetype = rng.choices(population=choices, weights=weights, k=1)[0]

            return archetype

        return None
