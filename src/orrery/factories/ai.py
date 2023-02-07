from typing import Any

from orrery.content_management import AIBrainLibrary
from orrery.core.ai import AIComponent
from orrery.core.ecs import IComponentFactory, World


class AIComponentFactory(IComponentFactory):
    def create(self, world: World, **kwargs: Any) -> AIComponent:
        brain_library = world.get_resource(AIBrainLibrary)
        brain = brain_library[kwargs["brain"]]
        return AIComponent(brain)
