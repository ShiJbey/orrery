import random
from typing import Any, List, Optional

from orrery import GameObject, World
from orrery.core.actions import Action
from orrery.core.ai import IAIBrain
from orrery.core.life_event import LifeEvent
from orrery.decorators import brain_factory
from orrery.orrery import Orrery, PluginInfo


class DefaultBrain(IAIBrain):
    def __init__(self) -> None:
        super().__init__()
        self.life_events: List[LifeEvent] = []
        self.actions: List[Action] = []

    def get_type(self) -> str:
        return self.__class__.__name__

    def get_next_location(self, world: World, gameobject: GameObject) -> Optional[int]:
        pass

    def execute_action(self, world: World, gameobject: GameObject) -> None:
        rng = world.get_resource(random.Random)
        if self.actions:
            chosen_action = rng.choice(self.actions)
            if chosen_action.is_valid(world):
                chosen_action.execute()
        self.actions.clear()

    def append_action(self, action: Action) -> None:
        self.actions.append(action)

    def append_life_event(self, event: LifeEvent) -> None:
        self.life_events.append(event)

    def select_life_event(self, world: World) -> Optional[LifeEvent]:
        rng = world.get_resource(random.Random)
        if self.life_events:
            chosen = rng.choice(self.life_events)
            if chosen.is_valid(world):
                return chosen

        return None


plugin_info: PluginInfo = {
    "name": "default ai plugin",
    "plugin_id": "default.ai",
    "version": "0.1.0",
}


def setup(sim: Orrery):
    @brain_factory(sim, "default")
    def default_brain_factory(**kwargs: Any) -> IAIBrain:
        return DefaultBrain()
