"""
This sample shows how to manually execute life events
"""
import random
from random import Random
from typing import Any, Dict, List, Optional

from orrery import (
    Component,
    GameObject,
    ISystem,
    Orrery,
    OrreryConfig,
    SimDateTime,
    World,
)
from orrery.components import Active, InTheWorkforce, Unemployed
from orrery.core.event import EventBuffer, EventHistory
from orrery.core.life_event import LifeEvent, LifeEventBuffer
from orrery.plugins.default.life_events import StartDatingLifeEvent
from orrery.utils.common import (
    add_character_to_settlement,
    spawn_character,
    spawn_settlement,
)
from orrery.utils.relationships import add_relationship, get_relationship

sim = Orrery(
    OrreryConfig.parse_obj(
        {
            "seed": 3,
            "relationship_schema": {
                "stats": {
                    "Friendship": {
                        "min_value": -100,
                        "max_value": 100,
                        "changes_with_time": True,
                    },
                    "Romance": {
                        "min_value": -100,
                        "max_value": 100,
                        "changes_with_time": True,
                    },
                },
            },
            "plugins": [
                "orrery.plugins.default.names",
                "orrery.plugins.default.characters",
                "orrery.plugins.default.life_events",
            ],
        }
    )
)


@sim.component()
class SimpleBrain(Component):
    def __init__(self) -> None:
        super().__init__()
        self.optional_events: List[LifeEvent] = []

    def append_life_event(self, event: LifeEvent) -> None:
        self.optional_events.append(event)

    def select_life_event(self, world: World) -> Optional[LifeEvent]:
        rng = world.get_resource(Random)
        if self.optional_events:
            chosen = rng.choice(self.optional_events)
            if chosen.is_valid(world):
                return chosen

        return None

    def to_dict(self) -> Dict[str, Any]:
        return {}


@sim.system()
class SimpleBrainSystem(ISystem):

    sys_group = "character-update"
    priority = -20

    def process(self, *args: Any, **kwargs: Any) -> None:
        brains = self.world.get_component(SimpleBrain)
        random.shuffle(brains)
        for guid, brain in brains:
            event = brain.select_life_event(self.world)
            if event:
                event.execute()
                self.world.get_resource(LifeEventBuffer).append(event)


class FindJob(LifeEvent):
    def __init__(
        self,
        date: SimDateTime,
        character: GameObject,
        business: GameObject,
        occupation: str,
    ):
        super().__init__(date, {"Character": character, "Business": business})
        self.occupation: str = occupation

    def execute(self) -> None:
        # print("Decided to find a job")
        pass

    @classmethod
    def instantiate(
        cls, world: World, bindings: Optional[Dict[str, GameObject]] = None
    ) -> Optional[LifeEvent]:
        character = bindings["Character"]
        business = bindings.get(
            "Business", world.get_gameobject(world.get_component(MockBiz)[0][0])
        )
        return cls(world.get_resource(SimDateTime), character, business, "worker")


@sim.component()
class MockBiz(Component):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name: str = name

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name}


@sim.system()
class FindAJobSystem(ISystem):
    sys_group = "character-update"

    def process(self, *args: Any, **kwargs: Any) -> None:
        business = self.world.get_gameobject(self.world.get_component(MockBiz)[0][0])
        for guid, _ in self.world.get_components((Active, InTheWorkforce, Unemployed)):
            gameobject = self.world.get_gameobject(guid)
            gameobject.get_component(SimpleBrain).append_life_event(
                FindJob(
                    self.world.get_resource(SimDateTime), gameobject, business, "worker"
                )
            )


@sim.system()
class LifeEventBufferSystem(ISystem):
    sys_group = "clean-up"

    def process(self, *args: Any, **kwargs: Any) -> None:
        life_event_buffer = self.world.get_resource(LifeEventBuffer)
        event_buffer = self.world.get_resource(EventBuffer)
        for event in life_event_buffer.iter_events():
            for _, gameobject in event.iter_roles():
                gameobject.get_component(EventHistory).append(event)
            event_buffer.append(event)
        life_event_buffer.clear()


def main():
    sim.world.add_resource(LifeEventBuffer())
    republic_city = spawn_settlement(sim.world, "Republic City")

    sim.world.spawn_gameobject(
        [MockBiz("Cabbage Corp."), EventHistory(), SimpleBrain()], "Cabbage Corp."
    )

    korra = spawn_character(
        sim.world,
        "character::default::female",
        first_name="Avatar",
        last_name="Korra",
        age=21,
    )
    korra.add_component(SimpleBrain())
    korra.add_component(EventHistory())

    add_character_to_settlement(korra, republic_city)

    asami = spawn_character(
        sim.world,
        "character::default::female",
        first_name="Asami",
        last_name="Sato",
        age=22,
    )
    asami.add_component(SimpleBrain())
    asami.add_component(EventHistory())

    add_character_to_settlement(asami, republic_city)

    add_relationship(korra, asami)
    add_relationship(asami, korra)

    get_relationship(korra, asami)["Romance"] += 5
    get_relationship(asami, korra)["Romance"] += 5

    event = StartDatingLifeEvent.instantiate(
        sim.world, {"Initiator": korra, "Other": asami}
    )

    print(event)

    sim.step()

    get_relationship(korra, asami)["Romance"] += 25
    get_relationship(asami, korra)["Romance"] += 25

    event = StartDatingLifeEvent.instantiate(
        sim.world, {"Initiator": korra, "Other": asami}
    )

    assert event

    event.get_initiator().get_component(SimpleBrain).append_life_event(event)

    sim.step()

    print(event.is_valid(sim.world))


if __name__ == "__main__":
    main()
