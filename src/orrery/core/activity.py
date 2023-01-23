from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterator, List, Optional, Set

from orrery.core.ecs import Component, IComponentFactory, World
from orrery.core.virtues import Virtues


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


class ActivityLibrary:
    """
    Repository of all the various activities that can exist
    in the simulated world

    Attributes
    ----------
    _next_id: int
        The unique identifier assigned to the next created
        activity instance
    _name_to_activity: Dict[str, Activity]
        Map of the names of activities to Activity instances
    _id_to_name: Dict[int, str]
        Map of the unique ids of activities to their names

    Notes
    -----
    This classes uses the flyweight design pattern to save
    memory space since many activities are shared between
    location instances.
    """

    __slots__ = "_next_id", "_name_to_activity", "_id_to_name"

    def __init__(self) -> None:
        self._next_id: int = 0
        self._name_to_activity: Dict[str, ActivityInstance] = {}
        self._id_to_name: Dict[int, str] = {}

    def __contains__(self, activity_name: str) -> bool:
        """Return True if a service type exists with the given name"""
        return activity_name.lower() in self._name_to_activity

    def __iter__(self) -> Iterator[ActivityInstance]:
        """Return iterator for the ActivityLibrary"""
        return self._name_to_activity.values().__iter__()

    def get(self, activity_name: str, create_new: bool = True) -> ActivityInstance:
        """
        Get an Activity instance and create a new one if a
        matching instance does not exist
        """
        lc_activity_name = activity_name.lower()

        if lc_activity_name in self._name_to_activity:
            return self._name_to_activity[lc_activity_name]

        if create_new is False:
            raise KeyError(f"No activity found with name {activity_name}")

        uid = self._next_id
        self._next_id = self._next_id + 1
        activity = ActivityInstance(uid, lc_activity_name)
        self._name_to_activity[lc_activity_name] = activity
        self._id_to_name[uid] = lc_activity_name
        return activity


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


class ActivitiesFactory(IComponentFactory):
    """Creates LikedActivities component instances"""

    def create(
        self, world: World, activities: Optional[List[str]] = None, **kwargs: Any
    ) -> Activities:

        activity_library = world.get_resource(ActivityLibrary)

        activity_names: List[str] = activities if activities else []

        return Activities(set([activity_library.get(name) for name in activity_names]))


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


class LikedActivitiesFactory(IComponentFactory):
    """Creates LikedActivities component instances"""

    def create(
        self, world: World, activities: Optional[List[str]] = None, **kwargs: Any
    ) -> LikedActivities:

        activity_library = world.get_resource(ActivityLibrary)

        activity_names: List[str] = activities if activities else []

        return LikedActivities(
            set([activity_library.get(name) for name in activity_names])
        )


class ActivityToVirtueMap:
    """
    Mapping of activities to character virtues.
    We use this class to determine what activities
    characters like to engage in based on their virtues
    """

    __slots__ = "mappings"

    def __init__(self) -> None:
        self.mappings: Dict[ActivityInstance, Virtues] = {}

    def add_by_name(self, world: World, activity_name: str, *virtues: str) -> None:
        """Add a new virtue to the mapping"""
        activity = world.get_resource(ActivityLibrary).get(activity_name)

        self.mappings[activity] = Virtues({v: 1 for v in virtues})
