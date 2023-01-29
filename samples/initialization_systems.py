"""
samples/initialization_systems.py

This sample shows how to use initialization systems to set up the simulation before
the first timestep.
"""
from typing import Any

from orrery import ISystem, Orrery
from orrery.components import Settlement
from orrery.utils.common import create_settlement

sim = Orrery()


@sim.system()
class InitializeMajorSettlements(ISystem):
    sys_group = "initialization"

    def process(self, *args: Any, **kwargs: Any) -> None:
        print("Setting up settlements...")
        create_settlement(self.world, "Winterfell")
        create_settlement(self.world, "The Cale of Arryn")
        create_settlement(self.world, "Casterly Rock")
        create_settlement(self.world, "King's Landing")
        create_settlement(self.world, "Highgarden")
        create_settlement(self.world, "Braavos")
        create_settlement(self.world, "Pentos")


def main():
    # We run the simulation for 10 timesteps, but the initialization
    # system group only runs once on the first timestep.
    for _ in range(10):
        sim.step()

    for guid, settlement in sim.world.get_component(Settlement):
        print(f"({guid}) {settlement.name}")


if __name__ == "__main__":
    main()
