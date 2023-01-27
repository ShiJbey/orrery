"""
test_traits.py

Tests orrery.core.traits
"""
import pytest

from orrery.core.ecs import ComponentNotFoundError
from orrery.core.traits import Trait, TraitManager
from orrery.orrery import Orrery
from orrery.utils.traits import add_trait, get_trait, has_trait, remove_trait


class Kind(Trait):
    excludes = {"Mean"}

    pass


class Mean(Trait):
    excludes = {"Kind"}

    pass


class Drunkard(Trait):
    pass


def test_add_trait() -> None:
    sim = Orrery()
    character = sim.world.spawn_gameobject([TraitManager()])
    add_trait(character, Kind())
    assert has_trait(character, Kind) is True


def test_add_incompatible_trait() -> None:
    sim = Orrery()
    character = sim.world.spawn_gameobject([TraitManager()])
    add_trait(character, Kind())
    assert has_trait(character, Kind) is True
    with pytest.raises(RuntimeError):
        add_trait(character, Mean())


def test_remove_trait() -> None:
    sim = Orrery()
    character = sim.world.spawn_gameobject([TraitManager()])
    add_trait(character, Kind())
    assert has_trait(character, Kind) is True
    remove_trait(character, Kind)
    assert has_trait(character, Kind) is False


def test_get_trait() -> None:
    sim = Orrery()
    character = sim.world.spawn_gameobject([TraitManager()])
    add_trait(character, Kind())
    assert has_trait(character, Kind) is True
    t = get_trait(character, Kind)
    assert t.__class__ == Kind
    with pytest.raises(ComponentNotFoundError):
        get_trait(character, Drunkard)
