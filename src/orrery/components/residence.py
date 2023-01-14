from __future__ import annotations

import random
import re
from typing import Any, Dict, List, Optional, Type

from ordered_set import OrderedSet

from orrery.core.config import ResidenceConfig
from orrery.core.ecs import Component, ComponentBundle, GameObject, World


class Residence(Component):
    """
    Residence is a place where characters live

    Attributes
    ----------
    owners: OrderedSet[int]
        Characters that currently own the residence
    former_owners: OrderedSet[int]
        Characters who owned the residence in the past
    residents: OrderedSet[int]
        All the characters who live at the residence (including non-owners)
    former_residents: OrderedSet[int]
        Characters who lived at this residence in the past
    settlement: int
        ID of the Settlement this residence belongs to
    """

    __slots__ = (
        "owners",
        "former_owners",
        "residents",
        "former_residents",
        "settlement",
        "config",
    )

    def __init__(self, config: ResidenceConfig, settlement: int) -> None:
        super(Component, self).__init__()
        self.config: ResidenceConfig = config
        self.settlement: int = settlement
        self.owners: OrderedSet[int] = OrderedSet([])
        self.former_owners: OrderedSet[int] = OrderedSet([])
        self.residents: OrderedSet[int] = OrderedSet([])
        self.former_residents: OrderedSet[int] = OrderedSet([])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "settlement": self.settlement,
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
    """
    Component attached to characters indicating that they live in the town

    Attributes
    ----------
    residence: int
        Unique ID of the Residence GameObject that the resident belongs to
    settlement: int
        Unique ID of the settlement that the resident's residence belongs to
    """

    __slots__ = "residence", "settlement"

    def __init__(self, residence: int, settlement: int) -> None:
        super(Component, self).__init__()
        self.residence: int = residence
        self.settlement: int = settlement

    def to_dict(self) -> Dict[str, Any]:
        return {"residence": self.residence, "settlement": self.settlement}


class Vacant(Component):
    """Tags a residence that does not currently have anyone living there"""

    pass


class ResidenceComponentBundle(ComponentBundle):
    """
    ComponentBundle for specifically constructing residence instances

    Attributes
    ----------
    name: str
        The name of the config associated with this bundle
    units: int
        The number of residential units in the building (allows for multifamily housing)
    unit_bundle: ComponentBundle
        The component bundle used to construct the individual residential units that
        belong to the building
    """

    __slots__ = "unit_bundle", "units", "name"

    def __init__(
        self,
        name: str,
        building_components: Dict[Type[Component], Dict[str, Any]],
        unit_components: Dict[Type[Component], Dict[str, Any]],
        units: int = 1,
    ) -> None:
        super().__init__(building_components)
        self.name: str = name
        self.unit_bundle: ComponentBundle = ComponentBundle(unit_components)
        self.units: int = units

    def spawn(
        self,
        world: World,
        overrides: Optional[Dict[Type[Component], Dict[str, Any]]] = None,
    ) -> GameObject:
        building = super().spawn(world, overrides)

        for _ in range(self.units):
            building.add_child(self.unit_bundle.spawn(world))

        return building


class ResidenceLibrary:
    """Collection factories that create residence entities"""

    __slots__ = "_registry", "_bundles"

    def __init__(self) -> None:
        self._registry: Dict[str, ResidenceConfig] = {}
        self._bundles: Dict[str, ResidenceComponentBundle] = {}

    def add(
        self, config: ResidenceConfig, bundle: Optional[ResidenceComponentBundle] = None
    ) -> None:
        """Register a new archetype by name"""
        self._registry[config.name] = config
        if bundle:
            self._bundles[config.name] = bundle

    def get_all(self) -> List[ResidenceConfig]:
        """Get all stored archetypes"""
        return list(self._registry.values())

    def get(self, name: str) -> ResidenceConfig:
        """Get an archetype by name"""
        return self._registry[name]

    def get_bundle(self, name: str) -> ResidenceComponentBundle:
        """Retrieve the ComponentBundle mapped to the given name"""
        return self._bundles[name]

    def get_matching_bundles(
        self, *bundle_names: str
    ) -> List[ResidenceComponentBundle]:
        """Get all component bundles that match the given regex strings"""

        matches: List[ResidenceComponentBundle] = []

        for name, bundle in self._bundles.items():
            if any([re.match(pattern, name) for pattern in bundle_names]):
                matches.append(bundle)

        return matches

    def choose_random(
        self,
        rng: random.Random,
    ) -> Optional[ResidenceComponentBundle]:
        """Performs a weighted random selection across all character archetypes"""
        choices: List[ResidenceConfig] = []
        weights: List[int] = []

        for config in self.get_all():
            if config.template is False:
                choices.append(config)
                weights.append(config.spawning.spawn_frequency)

        if choices:
            # Choose an archetype at random
            chosen_config = rng.choices(population=choices, weights=weights, k=1)[0]

            return self._bundles[chosen_config.name]
        else:
            return None
