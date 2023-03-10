"""
samples/using_statuses.py

This sample shows how to apply and remove statuses from characters.

Statuses are essentially components with a little extra tracking information.
You can use the world's ".get_component(s)(...)" methods to query for their
presence. The only requirement is that game objects have a StatusManager component
attached to user the add_status/has_status utility functions.

This sample builds on the using events sample and adds a pays taxes status to the
character to prevent them from having to pay again.
"""
from dataclasses import dataclass
from typing import Any, Dict

from orrery import Component, GameObject, ISystem, Orrery, OrreryConfig, SimDateTime
from orrery.core.event import Event, EventHandler, EventRole
from orrery.core.status import StatusComponent, StatusManager
from orrery.utils.statuses import add_status, has_status

sim = Orrery(OrreryConfig(verbose=False))


@sim.component()
@dataclass
class Actor(Component):
    name: str

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name}


@sim.component()
@dataclass
class Money(Component):
    amount: int

    def to_dict(self) -> Dict[str, Any]:
        return {"amount": self.amount}


@sim.component()
@dataclass
class Job(Component):
    title: str
    salary: int

    def to_dict(self) -> Dict[str, Any]:
        return {"title": self.title, "salary": self.salary}


@sim.component()
class PaysTaxes(StatusComponent):
    pass


@sim.system()
class SalarySystem(ISystem):
    sys_group = "character-update"

    def process(self, *args: Any, **kwargs: Any):
        for _, (actor, job, money) in self.world.get_components((Actor, Job, Money)):
            money.amount += job.salary // 12
            print(f"{actor.name} has ${money.amount}.")


@sim.system()
class BecomeMillionaireEventSystem(ISystem):

    sys_group = "character-update"

    def process(self, *args: Any, **kwargs: Any) -> None:
        for guid, money in self.world.get_component(Money):
            character = self.world.get_gameobject(guid)
            if money.amount > 1_000_000:
                self.world.get_resource(EventHandler).emit(
                    BecomeMillionaireEvent(
                        self.world.get_resource(SimDateTime), character
                    )
                )


class BecomeMillionaireEvent(Event):
    def __init__(self, date: SimDateTime, character: GameObject) -> None:
        super().__init__(
            name="become-millionaire",
            timestamp=date.to_iso_str(),
            roles=[EventRole("Character", character.uid)],
        )


@sim.system()
class OnBecomeMillionaireSystem(ISystem):

    sys_group = "event-listeners"

    def process(self, *args: Any, **kwargs: Any) -> None:
        date = self.world.get_resource(SimDateTime)
        for event in self.world.get_resource(EventHandler).iter_events_of_type(
            BecomeMillionaireEvent
        ):
            character = self.world.get_gameobject(event["Character"])
            actor = character.get_component(Actor)

            if not has_status(character, PaysTaxes):
                print(f"{actor.name} became a millionaire. Here comes the IRS")
                character.get_component(Money).amount -= 750_000
                add_status(character, PaysTaxes(str(date)))
            else:
                print(f"{actor.name} already paid their taxes.")


def main():
    sim.world.spawn_gameobject(
        [Actor("Alice"), Money(0), Job("Intern", 1_000_000), StatusManager()]
    )

    for _ in range(24):
        sim.step()


if __name__ == "__main__":
    main()
