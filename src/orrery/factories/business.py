from __future__ import annotations

from typing import Any, Dict, List

from orrery.components.business import Business, Services
from orrery.content_management import BusinessLibrary, ServiceLibrary
from orrery.core.ecs import Component, IComponentFactory, World
from orrery.core.tracery import Tracery


class ServicesFactory(IComponentFactory):
    """
    Factory class that creates instances of Services components
    """

    def create(self, world: World, **kwargs: Any) -> Component:
        service_list: List[str] = kwargs.get("services", [])
        service_library = world.get_resource(ServiceLibrary)
        return Services(set([service_library.get(s) for s in service_list]))


class BusinessFactory(IComponentFactory):
    """Constructs instances of Business components"""

    def create(self, world: World, **kwargs: Any) -> Component:
        name_pattern: str = kwargs["name"]
        employee_types: Dict[str, int] = {**kwargs.get("employees", {})}

        config_name = kwargs["config"]

        config = world.get_resource(BusinessLibrary).get(config_name).config

        name_generator = world.get_resource(Tracery)

        return Business(
            config=config,
            name=name_generator.generate(name_pattern),
            open_positions=employee_types,
        )
