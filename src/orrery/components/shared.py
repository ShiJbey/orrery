from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Iterator, Optional, Set

from ordered_set import OrderedSet

from orrery.core.ecs import Component
from orrery.core.status import StatusComponent


class Active(StatusComponent):
    """Tags a GameObject as active within the simulation"""

    pass


class FrequentedLocations(Component):
    """Tracks the locations that a character frequents"""

    __slots__ = "locations"

    def __init__(self, locations: Optional[Set[int]] = None) -> None:
        super().__init__()
        self.locations: Set[int] = locations if locations else set()

    def to_dict(self) -> Dict[str, Any]:
        return {"locations": list(self.locations)}

    def __str__(self) -> str:
        return super().__repr__()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.locations.__repr__()})"


class Building(Component):
    """
    Building components are attached to structures (like businesses and residences)
    that are currently present in the town.

    Attributes
    ----------
    building_type: str
        What kind of building is this
    lot: int
        ID of the lot this building is on
    settlement: int
        The ID of the settlement this building belongs to
    """

    __slots__ = "building_type", "lot", "settlement"

    def __init__(self, building_type: str, lot: int, settlement: int) -> None:
        super().__init__()
        self.building_type: str = building_type
        self.lot: int = lot
        self.settlement: int = settlement

    def to_dict(self) -> Dict[str, Any]:
        return {
            "building_type": self.building_type,
            "lot": self.lot,
            "settlement": self.settlement,
        }

    def __repr__(self):
        return "{}(settlement={}, building_type={}, lot={})".format(
            self.__class__.__name__,
            self.settlement,
            self.building_type,
            self.lot,
        )


class FrequentedBy(Component):
    """Tracks the characters that frequent a location"""

    __slots__ = "_characters"

    def __init__(self) -> None:
        super().__init__()
        self._characters: OrderedSet[int] = OrderedSet()

    def add(self, character: int) -> None:
        self._characters.add(character)

    def remove(self, character: int) -> None:
        self._characters.remove(character)

    def clear(self) -> None:
        self._characters.clear()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "characters": list(self._characters),
        }

    def __contains__(self, item: int) -> bool:
        return item in self._characters

    def __iter__(self) -> Iterator[int]:
        return self._characters.__iter__()

    def __repr__(self):
        return "{}({})".format(
            self.__class__.__name__,
            self._characters,
        )


class Location(Component):

    __slots__ = "entities_present"

    def __init__(
        self,
    ) -> None:
        super().__init__()
        self.entities_present: OrderedSet[int] = OrderedSet()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities_present": list(self.entities_present),
        }

    def __repr__(self):
        return "{}(entities={})".format(self.__class__.__name__, self.entities_present)


@dataclass
class CurrentSettlement(Component):
    settlement: int

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.settlement})"

    def to_dict(self) -> Dict[str, Any]:
        return {"settlement": self.settlement}


@dataclass
class Position2D(Component):
    x: float = 0.0
    y: float = 0.0

    @staticmethod
    def euclidian_distance(a: Position2D, b: Position2D) -> float:
        """Return the euclidian distance between two points"""
        return math.sqrt((b.x - a.x) ** 2 - (b.y - a.x) ** 2)

    def to_dict(self) -> Dict[str, Any]:
        return {"x": self.x, "y": self.y}
