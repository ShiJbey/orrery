import random

import pytest

from orrery.components.virtues import Virtues, VirtueType
from orrery.core.ecs import World
from orrery.factories.virtues import VirtuesFactory


def test_construct_virtue_vect() -> None:
    # Test that virtue vector defaults to all zeros
    vect_0 = Virtues()
    assert vect_0.to_array().sum() == 0  # type: ignore

    # Test that one can override virtue vector values
    vect_1 = Virtues({"HEALTH": 10, "POWER": 20, "TRADITION": -120})
    assert vect_1[VirtueType.HEALTH] == 10
    assert vect_1[VirtueType.POWER] == 20
    assert vect_1[VirtueType.TRADITION] == -50  # Should be clamped
    assert vect_1[VirtueType.AMBITION] == 0


def test_virtue_vect_compatibility() -> None:
    vect_0 = Virtues({"HEALTH": 10, "POWER": 20})
    vect_1 = Virtues({"HEALTH": 10, "POWER": 20})
    vect_2 = Virtues({"HEALTH": -10, "POWER": -20})
    vect_3 = Virtues({"HEALTH": 10, "POWER": 20, "TRADITION": 10})

    assert vect_0.compatibility(vect_1) == 1.0
    assert vect_0.compatibility(vect_2) == -1.0
    assert vect_0.compatibility(vect_3) == pytest.approx(0.91, 0.1)  # type: ignore


def test_virtue_vect_get_low_values() -> None:
    vect_0 = Virtues({"HEALTH": 10, "POWER": 20, "TRADITION": -10, "LUST": -35})

    assert set(vect_0.get_low_values(2)) == {VirtueType.TRADITION, VirtueType.LUST}


def test_virtue_vect_get_high_values() -> None:
    vect_0 = Virtues({"HEALTH": 10, "POWER": 20, "TRADITION": -10, "LUST": -35})

    assert set(vect_0.get_high_values(2)) == {VirtueType.HEALTH, VirtueType.POWER}


def test_virtue_vect_get_item() -> None:
    vect_1 = Virtues({"HEALTH": 10, "POWER": 20, "TRADITION": -120})
    assert vect_1[VirtueType.HEALTH] == 10
    assert vect_1[VirtueType.POWER] == 20
    assert vect_1[VirtueType.TRADITION] == -50  # Should be clamped
    assert vect_1[VirtueType.AMBITION] == 0


def test_virtue_vect_set_item() -> None:
    vect_1 = Virtues({"HEALTH": 10, "POWER": 20, "TRADITION": -120})
    assert vect_1[VirtueType.HEALTH] == 10
    vect_1[VirtueType.HEALTH] = 56
    assert vect_1[VirtueType.HEALTH] == 50


def test_virtue_vect_to_dict() -> None:
    vect_1 = Virtues({"HEALTH": 10, "POWER": 20, "TRADITION": -120})
    virtue_dict = vect_1.to_dict()

    assert virtue_dict["HEALTH"] == 10
    assert virtue_dict["POWER"] == 20
    assert virtue_dict["TRADITION"] == -50


def test_virtue_vect_factory() -> None:
    world = World()
    world.add_resource(random.Random(1234))
    factory = VirtuesFactory()
    vector: Virtues = factory.create(world, overrides={"ADVENTURE": 10, "POWER": 20})
    assert vector[VirtueType.ADVENTURE] == 10
    assert vector[VirtueType.POWER] == 20
