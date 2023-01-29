"""
test_status.py

TODO: Fill in the placeholder tests with actual tests
"""
from dataclasses import dataclass
from typing import Any, Dict

from orrery.core.ecs import Component, World
from orrery.core.status import StatusComponent, StatusManager
from orrery.core.time import SimDateTime
from orrery.utils.statuses import add_status, remove_status


@dataclass
class Stats(Component):
    strength: int = 0
    defense: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {"strength": self.strength, "defense": self.defense}


class SuperStrength(StatusComponent):
    pass


def test_status_on_add() -> None:
    """Test calling the Status.on_add method"""
    world = World()
    world.add_resource(SimDateTime(1, 1, 1))
    current_date = world.get_resource(SimDateTime).to_iso_str()

    gameobject = world.spawn_gameobject([Stats(), StatusManager()])

    assert gameobject.get_component(Stats).strength == 0

    add_status(gameobject, SuperStrength(current_date))

    assert gameobject.get_component(Stats).strength == 10


def test_status_on_remove() -> None:
    """Test calling the Status.on_remove method"""
    world = World()
    world.add_resource(SimDateTime(1, 1, 1))
    current_date = world.get_resource(SimDateTime).to_iso_str()

    gameobject = world.spawn_gameobject([Stats(), StatusManager()])

    assert gameobject.get_component(Stats).strength == 0

    add_status(gameobject, SuperStrength(current_date))

    assert gameobject.get_component(Stats).strength == 10

    remove_status(gameobject, SuperStrength)

    assert gameobject.get_component(Stats).strength == 0


def test_status_on_update() -> None:
    """Test calling the Status.on_update method"""
    assert False


def test_status_to_dict() -> None:
    """Test calling the Status.to_dict method"""
    assert False


def test_add_status() -> None:
    """Test calling the StatusManager.add method"""
    assert False


def test_get_status() -> None:
    """Test calling the StatusManager.add method"""
    assert False


def test_remove_status() -> None:
    """Test calling the StatusManager.add method"""
    assert False


def test_clear_statuses() -> None:
    """Test calling the StatusManager.add method"""
    assert False


def test_contains_status() -> None:
    """Test calling the StatusManager.__contains__ method"""
    assert False


def test_iter_statuses() -> None:
    """Test calling the StatusManager.__iter__ method"""
    assert False
