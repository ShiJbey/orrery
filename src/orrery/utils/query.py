from __future__ import annotations

from typing import List, Literal, Tuple, Type, Union

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
from orrery.components.relationship import Relationship, RelationshipManager
from orrery.core.ecs import GameObject, World
from orrery.core.ecs.query import (
    QueryClause,
    QueryContext,
    QueryGetFn,
    Relation,
    WithClause,
)
from orrery.core.status import StatusComponent
from orrery.utils.relationships import get_relationship_entity

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
    return WithClause(tuple(component_types), variable)


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


def filter_relationship_stat_gte(
    stat_name: str,
    threshold: float,
    value_type: Literal["raw", "scaled", "norm"] = "raw",
):
    """
    Filter function for an ECS query that returns True if the friendship
    value from one character to another is greater than or equal to a given threshold
    """

    def precondition(gameobject: GameObject) -> bool:
        relationship = gameobject.get_component(Relationship)
        if value_type == "raw":
            return relationship[stat_name].get_raw_value() >= threshold
        elif value_type == "scaled":
            return relationship[stat_name].get_scaled_value() >= threshold
        elif value_type == "norm":
            return relationship[stat_name].get_normalized_value() >= threshold
        else:
            raise RuntimeError(f"Unknown relationship stat value type, {value_type}")

    return precondition


def filter_relationship_stat_lte(
    stat_name: str,
    threshold: float,
    value_type: Literal["raw", "scaled", "norm"] = "raw",
):
    """
    Filter function for an ECS query that returns True if the friendship
    value from one character to another is greater than or equal to a given threshold
    """

    def precondition(gameobject: GameObject) -> bool:
        relationship = gameobject.get_component(Relationship)
        if value_type == "raw":
            return relationship[stat_name].get_raw_value() <= threshold
        elif value_type == "scaled":
            return relationship[stat_name].get_scaled_value() <= threshold
        elif value_type == "norm":
            return relationship[stat_name].get_normalized_value() <= threshold
        else:
            raise RuntimeError(f"Unknown relationship stat value type, {value_type}")

    return precondition


def find_with_relationship_stat_gte(
    stat_name: str,
    threshold: float,
    value_type: Literal["raw", "scaled", "norm"] = "raw",
) -> QueryGetFn:
    """
    Returns QueryGetFn that finds all the relationships of the first variable that have
    friendship scores greater than or equal to the threshold and binds them to the
    second variable
    """

    def clause(
        ctx: QueryContext, world: World, *variables: str
    ) -> List[Tuple[int, ...]]:

        if ctx.relation is None:
            raise TypeError("Relation is None inside query")

        # loop through each row in the ctx at the given column
        results: List[Tuple[int, ...]] = []

        subject_id: int
        for (subject_id,) in ctx.relation.get_as_tuple(slice(0, -1), variables[0]):
            subject = world.get_gameobject(subject_id)
            relationship_manager = subject.get_component(RelationshipManager)
            for target_id, rel_id in relationship_manager.relationships.items():
                relationship = world.get_gameobject(rel_id).get_component(Relationship)

                if value_type == "raw":
                    value = relationship[stat_name].get_raw_value()
                elif value_type == "scaled":
                    value = relationship[stat_name].get_scaled_value()
                elif value_type == "norm":
                    value = relationship[stat_name].get_normalized_value()
                else:
                    raise RuntimeError(
                        f"Unknown relationship stat value type, {value_type}"
                    )

                if value >= threshold:
                    results.append((subject_id, target_id))

        return results

    return clause


def find_with_relationship_stat_lte(
    stat_name: str,
    threshold: float,
    value_type: Literal["raw", "scaled", "norm"] = "raw",
) -> QueryGetFn:
    """
    Returns QueryGetFn that finds all the relationships of the first variable that have
    friendship scores greater than or equal to the threshold and binds them to the
    second variable
    """

    def clause(
        ctx: QueryContext, world: World, *variables: str
    ) -> List[Tuple[int, ...]]:

        if ctx.relation is None:
            raise TypeError("Relation is None inside query")

        # loop through each row in the ctx at the given column
        results: List[Tuple[int, ...]] = []

        subject_id: int
        for (subject_id,) in ctx.relation.get_as_tuple(slice(0, -1), variables[0]):
            subject = world.get_gameobject(subject_id)
            relationship_manager = subject.get_component(RelationshipManager)
            for target_id, rel_id in relationship_manager.relationships.items():
                relationship = world.get_gameobject(rel_id).get_component(Relationship)

                if value_type == "raw":
                    value = relationship[stat_name].get_raw_value()
                elif value_type == "scaled":
                    value = relationship[stat_name].get_scaled_value()
                elif value_type == "norm":
                    value = relationship[stat_name].get_normalized_value()
                else:
                    raise RuntimeError(
                        f"Unknown relationship stat value type, {value_type}"
                    )

                if value <= threshold:
                    results.append((subject_id, target_id))

        return results

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
    relationship = get_relationship_entity(a, b)
    family_status_types = [ChildOf, ParentOf, SiblingOf]
    return any([relationship.has_component(st) for st in family_status_types])
