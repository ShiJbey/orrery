from __future__ import annotations

from typing import Dict, Any, Set, Iterator, List

from orrery.ecs import Component, World, IComponentFactory


class Activity:
    """An activity that characters do at a location"""

    __slots__ = "_uid", "_name"

    def __init__(self, uid: int, name: str) -> None:
        self._uid = uid
        self._name = name

    @property
    def uid(self) -> int:
        return self._uid

    @property
    def name(self) -> str:
        return self._name

    def __hash__(self) -> int:
        return self._uid

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Activity):
            return self.uid == other.uid
        raise TypeError(f"Expected Activity but was {type(object)}")

    def __repr__(self) -> str:
        return f"Activity({self.name})"


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
        self._name_to_activity: Dict[str, Activity] = {}
        self._id_to_name: Dict[int, str] = {}

    def __contains__(self, activity_name: str) -> bool:
        """Return True if a service type exists with the given name"""
        return activity_name.lower() in self._name_to_activity

    def __iter__(self) -> Iterator[Activity]:
        """Return iterator for the ActivityLibrary"""
        return self._name_to_activity.values().__iter__()

    def get(self, activity_name: str, create_new: bool = True) -> Activity:
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
        activity = Activity(uid, lc_activity_name)
        self._name_to_activity[lc_activity_name] = activity
        self._id_to_name[uid] = lc_activity_name
        return activity


class ActivityManager(Component):
    """
    A collection of all the activities that characters
    can engage in at a location
    """

    __slots__ = "_activities"

    def __init__(self, activities: Set[Activity]) -> None:
        super().__init__()
        self._activities: Set[Activity] = activities

    def to_dict(self) -> Dict[str, Any]:
        return {**super().to_dict(), "activities": [a.name for a in self._activities]}

    def __contains__(self, activity: Activity) -> bool:
        return activity in self._activities

    def __str__(self) -> str:
        return super().__repr__()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._activities.__repr__()})"


class ActivityManagerFactory(IComponentFactory):
    def create(self, world: World, **kwargs: Any) -> Component:
        activity_library = world.get_resource(ActivityLibrary)

        activity_names: List[str] = kwargs.get("activities", [])

        return ActivityManager(
            set([activity_library.get(name) for name in activity_names])
        )


class LikedActivities(Component):

    __slots__ = "activities"

    def __init__(self, activities: Set[Activity]) -> None:
        super(Component, self).__init__()
        self.activities: Set[Activity] = activities

    def to_dict(self) -> Dict[str, Any]:
        return {**super().to_dict(), "activities": [a.name for a in self.activities]}

    def __contains__(self, activity: Activity) -> bool:
        return activity in self.activities

    def __str__(self) -> str:
        return super().__repr__()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.activities.__repr__()})"
