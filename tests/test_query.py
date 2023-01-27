from typing import Any, Dict

import pytest

from orrery.components.character import GameCharacter, Gender, Retired
from orrery.config import CharacterAgingConfig, CharacterConfig, CharacterSpawnConfig
from orrery.core.ecs import Component, World
from orrery.core.ecs.query import QueryBuilder, Relation
from orrery.core.time import SimDateTime
from orrery.utils.query import is_gender


def test_relation_create_empty():
    r0 = Relation.create_empty()
    assert r0.is_empty() is True
    assert r0.get_symbols() == ()

    r1 = Relation.create_empty("Apprentice", "Boss")
    assert r1.is_empty() is True
    assert r1.get_symbols() == ("Apprentice", "Boss")


def test_relation_from_bindings():
    r0 = Relation.from_bindings(Initiator=0, LoveInterest=1)
    assert r0.is_empty() is False
    assert r0.get_symbols() == ("Initiator", "LoveInterest")

    r0 = Relation.from_bindings(Rival=0, LoveInterest=1, Protagonist=4)
    assert r0.is_empty() is False
    assert r0.get_symbols() == ("Rival", "LoveInterest", "Protagonist")


def test_relation_get_symbols():
    r0 = Relation.create_empty("Employee", "OldEmployer", "NewEmployer")
    assert r0.get_symbols() == ("Employee", "OldEmployer", "NewEmployer")

    r1 = Relation.create_empty("Antagonist")
    assert r1.get_symbols() == ("Antagonist",)


def test_relation_is_empty():
    r0 = Relation.create_empty()
    assert r0.is_empty() is True

    r1 = Relation.create_empty("Hero", "DemonKing")
    assert r1.is_empty() is True


def test_relation_get_tuples():
    r0 = Relation(("Hero", "DemonKing"), [(1, 3), (1, 4), (1, 5)])
    assert r0.get_tuples() == [(1, 3), (1, 4), (1, 5)]

    r1 = Relation.from_bindings(Hero=1, DemonKing=4)
    assert r1.get_tuples() == [(1, 4)]


def test_relation_unify():

    r0 = Relation.create_empty()
    r1 = Relation(("Hero", "DemonKing"), [(1, 3), (1, 4), (1, 5)])
    r2 = Relation(("Hero", "LoveInterest"), [(1, 4), (2, 6)])
    r3 = Relation(("Rival",), [(5,), (3,)])

    # Test an empty Relation attempting to unify with a non-empty Relation
    assert r0.unify(r1).is_empty() is True
    assert r0.unify(r1).get_symbols() == ()
    assert r0.unify(r1).get_bindings() == []

    # Test a non-empty Relation attempting to unify with an empty Relation
    assert r1.unify(r0).is_empty() is True
    assert r1.unify(r0).get_symbols() == ()
    assert r1.unify(r0).get_bindings() == []

    # Test unify relations with shared symbols (DataFrame columns)
    assert r1.unify(r2).is_empty() is False
    assert r1.unify(r2).get_symbols() == ("Hero", "DemonKing", "LoveInterest")
    assert r1.unify(r2).get_tuples() == [
        (1, 3, 4),
        (1, 4, 4),
        (1, 5, 4),
    ]

    # Test unify relations without shared symbols
    assert r2.unify(r3).is_empty() is False
    assert r2.unify(r3).get_symbols() == ("Hero", "LoveInterest", "Rival")
    assert r2.unify(r3).get_tuples() == [(1, 4, 5), (1, 4, 3), (2, 6, 5), (2, 6, 3)]


def test_relation_copy():
    r0 = Relation.create_empty()
    r1 = r0.copy()
    assert id(r0) != id(r1)


class Hero(Component):
    def to_dict(self) -> Dict[str, Any]:
        return {}


class DemonKing(Component):
    def to_dict(self) -> Dict[str, Any]:
        return {}


@pytest.fixture()
def sample_world() -> World:
    world = World()

    character_config = CharacterConfig(
        name="human",
        aging=CharacterAgingConfig(
            adolescent_age=13,
            young_adult_age=18,
            adult_age=30,
            senior_age=65,
            lifespan=80,
        ),
        spawning=CharacterSpawnConfig(),
    )

    world.spawn_gameobject([Hero(), GameCharacter(character_config, "Shi", "", age=27)])
    world.spawn_gameobject(
        [
            Hero(),
            GameCharacter(character_config, "Astrid", "", gender=Gender.Female),
            Retired(SimDateTime().to_iso_str()),
        ]
    )
    world.spawn_gameobject(
        [
            DemonKing(),
            GameCharacter(character_config, "-Shi", ""),
            Retired(SimDateTime().to_iso_str()),
        ]
    )
    world.spawn_gameobject(
        [
            DemonKing(),
            GameCharacter(
                character_config, "Palpatine", "", age=160, gender=Gender.NonBinary
            ),
        ]
    )

    return world


def test_with(sample_world: World):
    query = QueryBuilder().with_((Hero,)).build()
    result = set(query.execute(sample_world))
    expected = {(1,), (2,)}
    assert result == expected

    query = QueryBuilder().with_((Hero, Retired)).build()
    result = set(query.execute(sample_world))
    expected = {(2,)}
    assert result == expected

    query = (
        QueryBuilder("HERO", "VILLAIN")
        .with_((GameCharacter, Hero), "HERO")
        .with_((DemonKing, Retired), "VILLAIN")
        .build()
    )
    result = set(query.execute(sample_world))
    expected = {(1, 3), (2, 3)}
    assert result == expected


# def test_without(sample_world: World):
#     query = QueryBuilder().with_((Hero,)).without_((Retired,)).build()
#     result = set(query.execute(sample_world))
#     expected = {(1,)}
#     assert result == expected

#     query = QueryBuilder().with_((GameCharacter, Gender)).without_((Hero,)).build()
#     result = set(query.execute(sample_world))
#     expected = {(4,)}
#     assert result == expected

#     query = (
#         QueryBuilder("Hero", "Villain")
#         .with_((GameCharacter, Hero), "Hero")
#         .with_((DemonKing,), "Villain")
#         .without_((Retired,), "Villain")
#         .build()
#     )
#     result = set(query.execute(sample_world))
#     expected = {(1, 4), (2, 4)}
#     assert result == expected

#     with pytest.raises(RuntimeError):
#         (QueryBuilder().without_((Retired,)).build().execute(sample_world))


def test_query_bindings(sample_world: World):

    query = QueryBuilder().with_((Hero,)).build()
    result = set(query.execute(sample_world, 2))
    expected = {(2,)}
    assert result == expected

    query = (
        QueryBuilder()
        .with_((GameCharacter,))
        .filter_(is_gender(Gender.NonBinary))
        .build()
    )
    result = set(query.execute(sample_world, 4))
    expected = {(4,)}
    assert result == expected

    query = (
        QueryBuilder("HERO", "VILLAIN")
        .with_((GameCharacter, Hero), "HERO")
        .with_((DemonKing, Retired), "VILLAIN")
        .build()
    )
    result = set(query.execute(sample_world, HERO=2))
    expected = {(2, 3)}
    assert result == expected


def test_filter(sample_world: World):
    query = (
        QueryBuilder()
        .with_((GameCharacter,))
        .filter_(
            lambda world, *gameobjects: gameobjects[0].get_component(GameCharacter).age
            > 25
        )
        .build()
    )
    result = set(query.execute(sample_world))
    expected = {(1,), (4,)}
    assert result == expected

    query = (
        QueryBuilder()
        .with_((GameCharacter,))
        .filter_(is_gender(Gender.NonBinary))
        .build()
    )
    result = set(query.execute(sample_world))
    expected = {(4,)}
    assert result == expected

    with pytest.raises(RuntimeError):
        QueryBuilder("X", "Y").filter_(
            lambda world, *gameobjects: gameobjects[0] == gameobjects[1], "X", "Y"
        ).build().execute(sample_world)
