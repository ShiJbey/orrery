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

    def add(self, location: int) -> None:
        self.locations.add(location)

    def remove(self, location: int) -> None:
        self.locations.remove(location)

    def clear(self) -> None:
        self.locations.clear()

    def to_dict(self) -> Dict[str, Any]:
        return {"locations": list(self.locations)}

    def __contains__(self, item: int) -> bool:
        return item in self.locations

    def __iter__(self) -> Iterator[int]:
        return self.locations.__iter__()

    def __str__(self) -> str:
        return self.__repr__()

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
    """

    __slots__ = "building_type"

    def __init__(self, building_type: str) -> None:
        super().__init__()
        self.building_type: str = building_type

    def to_dict(self) -> Dict[str, Any]:
        return {"building_type": self.building_type}

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return "{}(building_type={})".format(
            self.__class__.__name__,
            self.building_type,
        )


@dataclass
class CurrentLot(Component):
    """Tracks the lot that a building belongs to

    Attributes
    ----------
    lot: int
        The ID of a lot within a SettlementMap
    """

    lot: int

    def to_dict(self) -> Dict[str, Any]:
        return {"lot": self.lot}


class FrequentedBy(Component):
    """Tracks the characters that frequent a location"""

    __slots__ = "_characters"

    def __init__(self) -> None:
        super().__init__()
        self._characters: OrderedSet[int] = OrderedSet([])

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

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return "{}({})".format(
            self.__class__.__name__,
            self._characters,
        )


class Location(Component):
    """Marks a location as a place where GameObjects can be

    Locations track all present GameObjects and are used to find locations that
    characters can travel to.

    Attributes
    ----------
    entities_present: OrderedSet[int]
        All the GameObjects at this location
    """

    __slots__ = "entities_present"

    def __init__(
        self,
    ) -> None:
        super().__init__()
        self.entities_present: OrderedSet[int] = OrderedSet([])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities_present": list(self.entities_present),
        }

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return "{}(entities={})".format(self.__class__.__name__, self.entities_present)


@dataclass
class CurrentSettlement(Component):
    """Tracks the ID of the settlement that a GameObject is currently in

    Attributes
    ----------
    settlement: int
        The GameObject ID of a settlement
    """

    settlement: int

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.settlement})"

    def to_dict(self) -> Dict[str, Any]:
        return {"settlement": self.settlement}


@dataclass
class Position2D(Component):
    """The 2D position of a GameObject in the world

    Attributes
    ----------
    x: float
        The X-position
    y: float
        The Y-position
    """

    x: float = 0.0
    y: float = 0.0

    @staticmethod
    def euclidian_distance(a: Position2D, b: Position2D) -> float:
        """Return the euclidian distance between two points"""
        return math.sqrt((b.x - a.x) ** 2 - (b.y - a.x) ** 2)

    def to_dict(self) -> Dict[str, Any]:
        return {"x": self.x, "y": self.y}


@dataclass
class PrefabName(Component):
    """Tracks the ID of the settlement that a GameObject is currently in

    Attributes
    ----------
    prefab: str
        The name of the prefab used to construct this GameObject
    """

    prefab: str

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.prefab})"

    def to_dict(self) -> Dict[str, Any]:
        return {"prefab": self.prefab}
