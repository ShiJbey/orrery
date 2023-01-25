from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Set

from orrery.core.ecs import Component


@dataclass(frozen=True, slots=True)
class ActivityInstance:
    """
    An activity that characters do at a location

    Attributes
    ----------
    uid: int
        The unique identifier for this activity
    name: str
        The name of the activity
    """

    uid: int
    name: str

    def __hash__(self) -> int:
        return self.uid

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return self.name

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ActivityInstance):
            return self.uid == other.uid
        raise TypeError(f"Expected Activity but was {type(object)}")


class Activities(Component):
    """
    A collection of all the activities that characters can engage in at a location
    """

    __slots__ = "_activities"

    def __init__(self, activities: Set[ActivityInstance]) -> None:
        super().__init__()
        self._activities: Set[ActivityInstance] = activities

    def to_dict(self) -> Dict[str, Any]:
        return {"activities": [a.name for a in self._activities]}

    def __contains__(self, activity: ActivityInstance) -> bool:
        return activity in self._activities

    def __str__(self) -> str:
        return super().__repr__()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._activities.__repr__()})"


class LikedActivities(Component):
    """
    Collection of activities that a character likes to do

    Attributes
    ----------
    activities: Set[Activity]
        The set of activities that a character likes
    """

    __slots__ = "activities"

    def __init__(self, activities: Set[ActivityInstance]) -> None:
        super().__init__()
        self.activities: Set[ActivityInstance] = activities

    def to_dict(self) -> Dict[str, Any]:
        return {"activities": [a.name for a in self.activities]}

    def __contains__(self, activity: ActivityInstance) -> bool:
        return activity in self.activities

    def __str__(self) -> str:
        return super().__repr__()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.activities.__repr__()})"
