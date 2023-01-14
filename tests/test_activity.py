from typing import cast

from orrery.core.activity import (
    Activities,
    ActivitiesFactory,
    ActivityLibrary,
    ActivityToVirtueMap,
    LikedActivities,
)
from orrery.core.ecs import World
from orrery.core.virtues import VirtueType


def test_get_activity_from_library() -> None:
    activity_library = ActivityLibrary()
    running = activity_library.get("Running")
    running_other = activity_library.get("running")
    eating = activity_library.get("Eating")

    assert running is running_other
    assert running.uid == 0
    assert eating.uid == 1
    assert eating.name == "eating"


def test_iterate_activity_library() -> None:
    activity_library = ActivityLibrary()
    activity_library.get("Running")
    activity_library.get("Eating")
    activity_library.get("Drinking")
    activity_library.get("Socializing")
    activity_library.get("Shopping")

    all_activities = set([a.name for a in activity_library])
    assert all_activities == {
        "running",
        "eating",
        "drinking",
        "socializing",
        "shopping",
    }


def test_activity_library_contains() -> None:
    activity_library = ActivityLibrary()
    activity_library.get("Running")
    activity_library.get("Eating")
    activity_library.get("Drinking")

    assert ("running" in activity_library) is True
    assert ("Eating" in activity_library) is True
    assert ("socializing" in activity_library) is False
    assert ("shopping" in activity_library) is False


def test_activity_manager_contains() -> None:
    activity_library = ActivityLibrary()
    activity_library.get("Running")
    activity_library.get("Eating")
    activity_library.get("Drinking")
    activity_library.get("Socializing")
    activity_library.get("Shopping")

    activity_manager = Activities(
        {
            activity_library.get("Running"),
            activity_library.get("Eating"),
            activity_library.get("Drinking"),
        }
    )

    assert activity_library.get("Drinking") in activity_manager
    assert activity_library.get("Shopping") not in activity_manager


def test_activity_manager_to_dict() -> None:
    activity_library = ActivityLibrary()
    activity_library.get("Running")
    activity_library.get("Eating")
    activity_library.get("Drinking")
    activity_library.get("Socializing")
    activity_library.get("Shopping")

    activity_manager = Activities(
        {
            activity_library.get("Running"),
            activity_library.get("Eating"),
            activity_library.get("Drinking"),
        }
    )

    assert activity_manager.to_dict() == {
        "activities": ["running", "eating", "drinking"]
    }


def test_activity_manager_factory() -> None:
    world = World()

    activity_library = ActivityLibrary()
    activity_library.get("Running")
    activity_library.get("Eating")
    activity_library.get("Drinking")
    activity_library.get("Socializing")
    activity_library.get("Shopping")

    world.add_resource(activity_library)

    factory = ActivitiesFactory()

    activity_manager = cast(
        Activities, factory.create(world, activities=["Shopping", "Eating"])
    )

    assert activity_library.get("Drinking") not in activity_manager
    assert activity_library.get("Shopping") in activity_manager
    assert activity_library.get("Eating") in activity_manager


def test_liked_activities_contains() -> None:
    activity_library = ActivityLibrary()
    activity_library.get("Running")
    activity_library.get("Eating")
    activity_library.get("Drinking")
    activity_library.get("Socializing")
    activity_library.get("Shopping")

    liked_activities = LikedActivities(
        {activity_library.get("socializing"), activity_library.get("shopping")}
    )

    assert activity_library.get("drinking") not in liked_activities
    assert activity_library.get("eating") not in liked_activities
    assert activity_library.get("socializing") in liked_activities


def test_liked_activities_to_dict() -> None:
    activity_library = ActivityLibrary()
    activity_library.get("Running")
    activity_library.get("Eating")
    activity_library.get("Drinking")
    activity_library.get("Socializing")
    activity_library.get("Shopping")

    liked_activities = LikedActivities(
        {activity_library.get("socializing"), activity_library.get("shopping")}
    )

    assert liked_activities.to_dict() == {"activities": ["socializing", "shopping"]}


def test_activity_virtue_map() -> None:
    activity_library = ActivityLibrary()

    activity_library.get("Running")
    activity_library.get("Eating")
    activity_library.get("Drinking")
    activity_library.get("Socializing")
    activity_library.get("Shopping")

    world = World()
    world.add_resource(activity_library)

    virtue_map = ActivityToVirtueMap()

    virtue_map.add_by_name(world, "Running", "HEALTH")

    assert (
        virtue_map.mappings[activity_library.get("Running")].to_array()[
            VirtueType.HEALTH
        ]
        == 1
    )

    assert (
        virtue_map.mappings[activity_library.get("Running")].to_array()[
            VirtueType.POWER
        ]
        == 0
    )
