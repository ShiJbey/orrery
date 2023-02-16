from typing import Optional

from orrery.components import Virtues
from orrery.core.ecs import GameObject
from orrery.orrery import Orrery, PluginInfo
from orrery.utils.common import location_has_activities

plugin_info: PluginInfo = {
    "name": "default location bias rules plugin",
    "plugin_id": "default.location_bias_rules",
    "version": "0.1.0",
}


def virtue_to_activity_bias(virtue: str, activity: str, modifier: int):
    def rule(character: GameObject, location: GameObject) -> Optional[int]:
        if virtues := character.try_component(Virtues):
            if virtue in virtues.get_high_values() and location_has_activities(
                location, activity
            ):
                return modifier

    return rule


def setup(sim: Orrery):

    # Show how to use the decorator

    @sim.location_bias_rule("leisure time values rest")
    def rule(character: GameObject, location: GameObject) -> Optional[int]:
        if virtues := character.try_component(Virtues):
            if "LEISURE_TIME" in virtues.get_high_values() and location_has_activities(
                location, "rest"
            ):
                return 1

    @sim.location_bias_rule("wealth likes gambling")
    def rule(character: GameObject, location: GameObject) -> Optional[int]:
        if virtues := character.try_component(Virtues):
            if "WEALTH" in virtues.get_high_values() and location_has_activities(
                location, "gambling"
            ):
                return 1

    @sim.location_bias_rule("excitement likes gambling")
    def rule(character: GameObject, location: GameObject) -> Optional[int]:
        if virtues := character.try_component(Virtues):
            if "EXCITEMENT" in virtues.get_high_values() and location_has_activities(
                location, "gambling"
            ):
                return 1

    @sim.location_bias_rule("adventure likes gambling")
    def rule(character: GameObject, location: GameObject) -> Optional[int]:
        if virtues := character.try_component(Virtues):
            if "ADVENTURE" in virtues.get_high_values() and location_has_activities(
                location, "gambling"
            ):
                return 1

    # For sake of time, use helper the method
    sim.add_location_bias_rule(virtue_to_activity_bias("LUST", "Gambling", 1))
    sim.add_location_bias_rule(
        virtue_to_activity_bias("MATERIAL_THINGS", "Shopping", 1)
    )
    sim.add_location_bias_rule(virtue_to_activity_bias("EXCITEMENT", "Shopping", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias("LEISURE_TIME", "Shopping", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias("HEALTH", "Recreation", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias("EXCITEMENT", "Recreation", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias("KNOWLEDGE", "Studying", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias("POWER", "Studying", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias("AMBITION", "Studying", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias("KNOWLEDGE", "Reading", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias("POWER", "Reading", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias("LEISURE_TIME", "Reading", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias("RELIABILITY", "Errands", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias("HEALTH", "Errands", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias("FAMILY", "Errands", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias("SOCIAL", "Eating", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias("HEALTH", "Eating", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias("FAMILY", "Eating", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias("SOCIAL", "Socializing", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias("EXCITEMENT", "Socializing", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias("FRIENDSHIP", "Socializing", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias("SOCIAL", "Drinking", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias("FRIENDSHIP", "Drinking", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias("HEALTH", "Relaxing", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias("TRANQUILITY", "Relaxing", 1))
    sim.add_location_bias_rule(virtue_to_activity_bias("LEISURE_TIME", "Relaxing", 1))
