from typing import Type, TypeVar

from orrery.core.ecs import GameObject
from orrery.core.traits import Trait, TraitManager

_T = TypeVar("_T", bound=Trait)


def add_trait(character: GameObject, trait: Trait) -> None:
    """Add a trait to a character

    Parameters
    ----------
    character: GameObject
        The character to add the trait to
    trait: Trait
        The trait to add
    """
    character.get_component(TraitManager).add(type(trait))
    character.add_component(trait)


def get_trait(character: GameObject, trait_type: Type[_T]) -> _T:
    """Get a trait from a character

    Parameters
    ----------
    character: GameObject
        The character to get the trait from
    trait_type: Type[_T]
        The type of trait to get

    Returns
    -------
    _T
        The instance of the desired trait type
    """
    return character.get_component(trait_type)


def remove_trait(character: GameObject, trait_type: Type[Trait]) -> None:
    """Remove a trait from a character

    Parameters
    ----------
    character: GameObject
        The character to remove the trait from
    trait_type: Type[Trait]
        The type of trait to remove
    """
    character.get_component(TraitManager).remove(trait_type)
    character.remove_component(trait_type)


def has_trait(character: GameObject, trait_type: Type[Trait]) -> bool:
    """Check if a character has a trait

    Parameters
    ----------
    character: GameObject
        The character to check
    trait_type: Type[Trait]
        The trait type to check for

    Returns
    -------
    bool
        True if the character has the given trait type
    """
    return character.has_component(trait_type)
