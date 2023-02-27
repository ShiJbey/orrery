from typing import Optional

from orrery.components import Virtues
from orrery.components.virtues import Virtue
from orrery.core.ecs import GameObject
from orrery.orrery import Orrery, PluginInfo
from orrery.utils.common import location_has_activities

plugin_info: PluginInfo = {
    "name": "default location bias rules plugin",
    "plugin_id": "default.location_bias_rules",
    "version": "0.1.0",
}


def virtue_to_activity_bias(virtue: Virtue, activity: str, modifier: int):
    def rule(character: GameObject, location: GameObject) -> Optional[int]:
        if virtues := character.try_component(Virtues):
            if virtue in virtues.get_high_values() and location_has_activities(
                location, activity
            ):
                return modifier

    return rule


def setup(sim: Orrery):

    # For sake of time, use helper the method
    sim.add_location_bias_rule(virtue_to_activity_bias(Virtue.LEISURE_TIME, "Rest", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias(Virtue.WEALTH, "Gambling", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias(Virtue.EXCITEMENT, "Gambling", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias(Virtue.ADVENTURE, "Gambling", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias(Virtue.LUST, "Gambling", 1))
    sim.add_location_bias_rule(
        virtue_to_activity_bias(Virtue.MATERIAL_THINGS, "Shopping", 1)
    )
    sim.add_location_bias_rule(virtue_to_activity_bias(Virtue.EXCITEMENT, "Shopping", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias(Virtue.LEISURE_TIME, "Shopping", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias(Virtue.HEALTH, "Recreation", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias(Virtue.EXCITEMENT, "Recreation", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias(Virtue.KNOWLEDGE, "Studying", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias(Virtue.POWER, "Studying", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias(Virtue.AMBITION, "Studying", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias(Virtue.KNOWLEDGE, "Reading", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias(Virtue.POWER, "Reading", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias(Virtue.LEISURE_TIME, "Reading", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias(Virtue.RELIABILITY, "Errands", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias(Virtue.HEALTH, "Errands", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias(Virtue.FAMILY, "Errands", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias(Virtue.SOCIALIZING, "Eating", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias(Virtue.HEALTH, "Eating", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias(Virtue.FAMILY, "Eating", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias(Virtue.SOCIALIZING, "Socializing", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias(Virtue.EXCITEMENT, "Socializing", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias(Virtue.FRIENDSHIP, "Socializing", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias(Virtue.SOCIALIZING, "Drinking", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias(Virtue.FRIENDSHIP, "Drinking", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias(Virtue.HEALTH, "Relaxing", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias(Virtue.TRANQUILITY, "Relaxing", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias(Virtue.LEISURE_TIME, "Relaxing", 1))
