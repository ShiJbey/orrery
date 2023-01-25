from __future__ import annotations

from typing import Any, List, Optional

from orrery.components.shared import FrequentedLocations, Location
from orrery.content_management import ActivityLibrary
from orrery.core.ecs import IComponentFactory, World


class FrequentedLocationsFactory(IComponentFactory):
    """Factory that create Location component instances"""

    def create(
        self, world: World, locations: Optional[List[int]] = None, **kwargs: Any
    ) -> FrequentedLocations:
        return FrequentedLocations(set(locations if locations else []))


class LocationFactory(IComponentFactory):
    """Factory that create Location component instances"""

    def create(
        self, world: World, activities: Optional[List[str]] = None, **kwargs: Any
    ) -> Location:
        activity_library = world.get_resource(ActivityLibrary)

        activity_names: List[str] = activities if activities else []

        return Location(set([activity_library.get(name) for name in activity_names]))
