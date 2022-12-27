from typing import Any, Dict, Set

from orrery.ecs import Component


class Name(Component):
    """The name of the GameObject"""

    __slots__ = "name"

    def __init__(self, name: str) -> None:
        super(Component, self).__init__()
        self.name: str = name

    def to_dict(self) -> Dict[str, Any]:
        return {**super().to_dict(), "name": self.name}

    def __str__(self) -> str:
        return self.name

    def __repr__(self):
        return f"{self.__class__.__name__}({self.name})"


class Location(Component):

    __slots__ = "frequented_by"

    def __init__(self) -> None:
        super(Component, self).__init__()
        self.frequented_by: Set[int] = set()


class Actor(Component):
    def __init__(self, first_name: str, last_name: str, age: int = 0) -> None:
        super(Component, self).__init__()
        self.first_name: str = first_name
        self.last_name: str = last_name
        self.age: float = float(age)


class FrequentedLocations(Component):

    __slots__ = "locations"

    def __init__(self, locations: Set[int]) -> None:
        super(Component, self).__init__()
        self.locations: Set[int] = locations

    def to_dict(self) -> Dict[str, Any]:
        return {**super().to_dict(), "locations": list(self.locations)}

    def __contains__(self, location: int) -> bool:
        return location in self.locations

    def __str__(self) -> str:
        return super().__repr__()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.locations.__repr__()})"
