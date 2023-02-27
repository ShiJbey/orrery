from typing import Dict, Type

from orrery.components import Virtues
from orrery.core.ecs import GameObject
from orrery.core.relationship import Friendship, RelationshipStat, Romance
from orrery.orrery import Orrery, PluginInfo

plugin_info: PluginInfo = {
    "name": "default location bias rules plugin",
    "plugin_id": "default.location_bias_rules",
    "version": "0.1.0",
}

def virtue_compatibility_rule(subject: GameObject, target: GameObject) -> Dict[Type[RelationshipStat], int]:
        if not subject.has_component(Virtues) or not target.has_component(Virtues):
            return {}

        character_virtues = subject.get_component(Virtues)
        acquaintance_virtues = target.get_component(Virtues)

        compatibility = character_virtues.compatibility(acquaintance_virtues)

        if compatibility < -50:
            return {Friendship: -2, Romance: -3}

        elif compatibility < 0:
            return {Friendship: -1, Romance: -2}

        elif compatibility < 50:
            return {Friendship: 1, Romance: 2}

        else:
            return {Friendship: 2, Romance: 3}



def setup(sim: Orrery):
    sim.add_social_rule(virtue_compatibility_rule, "virtue compatibility")
