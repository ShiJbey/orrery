from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from orrery.core.activity import ActivityInstance, ActivityLibrary
from orrery.core.ecs import Component, IComponentFactory, World
from orrery.core.status import StatusComponent


class Active(StatusComponent):
    """Tags a GameObject as active within the simulation"""

    pass


class FrequentedLocations(Component):

    __slots__ = "locations"

    def __init__(self, locations: Optional[Set[int]] = None) -> None:
        super().__init__()
        self.locations: Set[int] = locations if locations else set()

    def to_dict(self) -> Dict[str, Any]:
        return {"locations": list(self.locations)}

    def __contains__(self, location: int) -> bool:
        return location in self.locations

    def __str__(self) -> str:
        return super().__repr__()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.locations.__repr__()})"


class FrequentedLocationsFactory(IComponentFactory):
    """Factory that create Location component instances"""

    def create(
        self, world: World, locations: Optional[List[int]] = None, **kwargs: Any
    ) -> FrequentedLocations:
        return FrequentedLocations(set(locations if locations else []))


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


class Name(Component):
    """The name of the GameObject"""

    __slots__ = "name"

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name: str = name

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name}

    def __str__(self) -> str:
        return self.name

    def __repr__(self):
        return f"{self.__class__.__name__}({self.name})"


class Location(Component):

    __slots__ = "frequented_by", "activities"

    def __init__(self, activities: Optional[Set[ActivityInstance]] = None) -> None:
        super().__init__()
        self.frequented_by: Set[int] = set()
        self.activities: Set[ActivityInstance] = activities if activities else set()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frequented_by": list(self.frequented_by),
            "activities": [str(a) for a in self.activities],
        }

    def __repr__(self):
        return "{}(activities={}, frequented_by={})".format(
            self.__class__.__name__,
            self.activities,
            self.frequented_by,
        )


class LocationFactory(IComponentFactory):
    """Factory that create Location component instances"""

    def create(
        self, world: World, activities: Optional[List[str]] = None, **kwargs: Any
    ) -> Location:
        activity_library = world.get_resource(ActivityLibrary)

        activity_names: List[str] = activities if activities else []

        return Location(set([activity_library.get(name) for name in activity_names]))


@dataclass
class CurrentSettlement(Component):
    settlement_id: int

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.settlement_id})"

    def to_dict(self) -> Dict[str, Any]:
        return {"settlement_id": self.settlement_id}


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
