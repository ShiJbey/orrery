import json

from orrery.core.serializable import ISerializable
from orrery.orrery import Orrery


def export_to_json(sim: Orrery) -> str:
    return json.dumps(
        {
            "seed": sim.config.seed,
            "gameobjects": {g.id: g.to_dict() for g in sim.world.get_gameobjects()},
            "resources": {
                r.__class__.__name__: r.to_dict()
                for r in sim.world.get_all_resources()
                if isinstance(r, ISerializable)
            },
        }
    )
