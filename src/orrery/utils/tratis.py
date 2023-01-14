from orrery.core.ecs import GameObject, World
from orrery.core.traits import TraitLibrary, Traits


def add_trait(world: World, character: GameObject, trait_name: str) -> None:
    """Helper function for adding a trait to a character"""
    character.get_component(Traits).add_trait(
        world.get_resource(TraitLibrary).get(trait_name)
    )


def remove_trait(world: World, character: GameObject, trait_name: str) -> None:
    """Helper function for removing a trait from a character"""
    trait = world.get_resource(TraitLibrary).get(trait_name)
    traits = character.get_component(Traits)
    if trait in traits:
        traits.remove_trait(trait)


def has_trait(world: World, character: GameObject, trait_name: str) -> bool:
    """Utility function for checking if a character has a trait"""
    trait = world.get_resource(TraitLibrary).get(trait_name)
    traits = character.get_component(Traits)
    return trait in traits
