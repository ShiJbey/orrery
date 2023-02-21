from __future__ import annotations

from typing import Tuple, Type, Union

from orrery import Component
from orrery.components.business import Occupation, WorkHistory
from orrery.components.character import (
    ChildOf,
    Dating,
    GameCharacter,
    Gender,
    LifeStage,
    Married,
    ParentOf,
    SiblingOf,
)
from orrery.core.ecs import GameObject
from orrery.core.ecs.query import QueryClause, QueryContext, Relation, WithClause
from orrery.core.relationship import Relationship, RelationshipManager
from orrery.core.status import StatusComponent
from orrery.utils.relationships import get_relationship

###############################
# Entire Clauses
###############################


def with_components(
    variable: str, component_types: Union[Type[Component], Tuple[Type[Component], ...]]
) -> QueryClause:
    return WithClause(tuple(component_types), variable)


def with_statuses(
    variable: str, component_types: Union[Type[Component], Tuple[Type[Component], ...]]
) -> QueryClause:
    if isinstance(component_types, tuple):
        return WithClause(component_types, variable)
    return WithClause((component_types,), variable)


def with_relationship(
    owner_var: str,
    target_var: str,
    relationship_var: str,
    *statuses: Type[StatusComponent],
) -> QueryClause:
    def clause(ctx: QueryContext) -> Relation:
        results = []
        for rel_id, relationship in ctx.world.get_component(Relationship):
            r = ctx.world.get_gameobject(rel_id)

            if statuses and not r.has_components(*statuses):
                continue

            results.append((relationship.owner, relationship.target, rel_id))
        return Relation((owner_var, target_var, relationship_var), results)

    return clause


def life_stage_eq(stage: LifeStage):
    def fn(gameobject: GameObject) -> bool:
        character = gameobject.try_component(GameCharacter)
        if character is not None:
            return character.life_stage == stage
        return False

    return fn


def life_stage_ge(stage: LifeStage):
    def fn(gameobject: GameObject) -> bool:
        character = gameobject.try_component(GameCharacter)
        if character is not None:
            return character.life_stage >= stage
        return False

    return fn


def life_stage_le(stage: LifeStage):
    def fn(gameobject: GameObject) -> bool:
        character = gameobject.try_component(GameCharacter)
        if character is not None:
            return character.life_stage <= stage
        return False

    return fn


def over_age(age: int):
    def fn(gameobject: GameObject) -> bool:
        character = gameobject.try_component(GameCharacter)
        if character is not None:
            return character.age > age
        return False

    return fn


def is_gender(gender: Gender):
    """Return precondition function that checks if an entity is a given gender"""

    def fn(gameobject: GameObject) -> bool:
        if character := gameobject.try_component(GameCharacter):
            return character.gender == gender
        return False

    return fn


def has_work_experience_filter(occupation_type: str, years_experience: int = 0):
    """
    Returns Precondition function that returns true if the entity
    has experience as a given occupation type.

    Parameters
    ----------
    occupation_type: str
        The name of the occupation to check for
    years_experience: int
        The number of years of experience the entity needs to have
    """

    def fn(gameobject: GameObject) -> bool:
        total_experience: float = 0

        work_history = gameobject.try_component(WorkHistory)

        if work_history is None:
            return False

        for entry in work_history.entries[:-1]:
            if entry.occupation_type == occupation_type:
                total_experience += entry.years_held

        if gameobject.has_component(Occupation):
            occupation = gameobject.get_component(Occupation)
            if occupation.occupation_type == occupation_type:
                total_experience += occupation.years_held

        return total_experience >= years_experience

    return fn


def is_single(gameobject: GameObject) -> bool:
    """Return true if the character is not dating or married"""
    for _, rel_id in gameobject.get_component(
        RelationshipManager
    ).relationships.items():
        relationship = gameobject.world.get_gameobject(rel_id)
        if relationship.has_component(Dating) or relationship.has_component(Married):
            return False
    return True


def are_related(a: GameObject, b: GameObject) -> bool:
    relationship = get_relationship(a, b)
    family_status_types = [ChildOf, ParentOf, SiblingOf]
    return any([relationship.has_component(st) for st in family_status_types])
