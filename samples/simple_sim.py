import logging
import time
from typing import Any

from orrery import ISystem, Orrery, OrreryConfig, SimDateTime
from orrery.exporter import export_to_json
from orrery.utils.common import spawn_settlement

EXPORT_WORLD = False
DEBUG_LOGGING = False

sim = Orrery(
    OrreryConfig.parse_obj(
        {
            "seed": 8080,
            "relationship_schema": {
                "components": {
                    "Friendship": {
                        "min_value": -100,
                        "max_value": 100,
                    },
                    "Romance": {
                        "min_value": -100,
                        "max_value": 100,
                    },
                    "InteractionScore": {
                        "min_value": -5,
                        "max_value": 5,
                    },
                }
            },
            "plugins": [
                "orrery.plugins.default.names",
                "orrery.plugins.default.characters",
                "orrery.plugins.default.businesses",
                "orrery.plugins.default.residences",
                "orrery.plugins.default.life_events",
                "orrery.plugins.default.ai",
            ],
            "settings": {"new_families_per_year": 10},
        }
    )
)


@sim.system()
class CreateTown(ISystem):
    sys_group = "initialization"

    def process(self, *args: Any, **kwargs: Any) -> None:
        spawn_settlement(self.world)


if __name__ == "__main__":

    if DEBUG_LOGGING:
        logging.basicConfig(level=logging.DEBUG)

    print(f"Generating with world seed: {sim.config.seed}")

    st = time.time()
    sim.run_for(140)
    elapsed_time = time.time() - st

    print(f"World Date: {sim.world.get_resource(SimDateTime)}")
    print("Execution time: ", elapsed_time, "seconds")

    if EXPORT_WORLD:
        output_path = f"{sim.config.seed}_orrery.json"

        with open(output_path, "w") as f:
            f.write(export_to_json(sim))
            print(f"Simulation data written to: '{output_path}'")
