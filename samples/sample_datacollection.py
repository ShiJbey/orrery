from dataclasses import dataclass
from typing import Any, Dict

from orrery.core.ecs import Component, ISystem
from orrery.core.time import SimDateTime
from orrery.data_collection import DataCollector
from orrery.orrery import Orrery, OrreryConfig

app = Orrery(OrreryConfig(seed=101))


@app.component()
@dataclass
class Actor(Component):
    name: str

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name}


@app.component()
@dataclass
class Money(Component):
    amount: int

    def to_dict(self) -> Dict[str, Any]:
        return {"amount": self.amount}


@app.component()
@dataclass
class Job(Component):
    title: str
    salary: int

    def to_dict(self) -> Dict[str, Any]:
        return {"title": self.title, "salary": self.salary}


@app.system()
class SalarySystem(ISystem):
    def process(self, *args: Any, **kwargs: Any):
        job: Job
        money: Money
        for _, (job, money) in self.world.get_components(Job, Money):
            money.amount += job.salary // 12


@app.system(-1000)
class WealthReporter(ISystem):
    def process(self, *args, **kwargs):
        timestamp = self.world.get_resource(SimDateTime).to_iso_str()
        data_collector = self.world.get_resource(DataCollector)
        for guid, money in self.world.get_component(Money):
            data_collector.add_table_row(
                "wealth", {"uid": guid, "timestamp": timestamp, "money": money.amount}
            )


if __name__ == "__main__":
    app.world.add_resource(DataCollector())

    app.world.get_resource(DataCollector).create_new_table(
        "wealth", ("uid", "timestamp", "money")
    )

    app.world.spawn_gameobject([Actor("Alice"), Money(0), Job("WacArnolds", 32_000)])

    for _ in range(12):
        app.step()

    data_frame = app.world.get_resource(DataCollector).get_table_dataframe("wealth")

    print(data_frame)
