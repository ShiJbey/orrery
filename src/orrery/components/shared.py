from dataclasses import dataclass
from typing import Any, Dict, Optional, Set

from orrery.core.ecs import Component


class Active(Component):
    """Tags a GameObject as active within the simulation"""

    pass


class FrequentedLocations(Component):

    __slots__ = "locations"

    def __init__(self, locations: Optional[Set[int]] = None) -> None:
        super(Component, self).__init__()
        self.locations: Set[int] = locations if locations else set()

    def to_dict(self) -> Dict[str, Any]:
        return {"locations": list(self.locations)}

    def __contains__(self, location: int) -> bool:
        return location in self.locations

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
    """

    __slots__ = "building_type", "lot", "settlement"

    def __init__(self, building_type: str, lot: int, settlement: int) -> None:
        super(Component, self).__init__()
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
        super(Component, self).__init__()
        self.name: str = name

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name}

    def __str__(self) -> str:
        return self.name

    def __repr__(self):
        return f"{self.__class__.__name__}({self.name})"


class Location(Component):

    __slots__ = "frequented_by"

    def __init__(self) -> None:
        super(Component, self).__init__()
        self.frequented_by: Set[int] = set()

    def to_dict(self) -> Dict[str, Any]:
        return {"frequented_by": list(self.frequented_by)}

    def __repr__(self):
        return f"{self.__class__.__name__}({self.frequented_by})"


@dataclass
class Position2D(Component):
    x: float = 0.0
    y: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {**super().to_dict(), "x": self.x, "y": self.y}
