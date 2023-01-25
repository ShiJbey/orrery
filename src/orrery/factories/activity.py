from __future__ import annotations

from typing import Any, List, Optional

from orrery.components.activity import Activities, LikedActivities
from orrery.content_management import ActivityLibrary
from orrery.core.ecs import IComponentFactory, World


class ActivitiesFactory(IComponentFactory):
    """Creates LikedActivities component instances"""

    def create(
        self, world: World, activities: Optional[List[str]] = None, **kwargs: Any
    ) -> Activities:

        activity_library = world.get_resource(ActivityLibrary)

        activity_names: List[str] = activities if activities else []

        return Activities(set([activity_library.get(name) for name in activity_names]))


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
