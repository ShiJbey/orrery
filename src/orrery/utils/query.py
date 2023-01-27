from __future__ import annotations

import random
from typing import List, Literal, Optional, Tuple, Type

from orrery.components.business import Occupation, WorkHistory
from orrery.components.character import (
    Dating,
    GameCharacter,
    Gender,
    LifeStage,
    Married,
)
from orrery.components.relationship import Relationship, RelationshipManager
from orrery.core.ecs import Component, GameObject, World
from orrery.core.ecs.query import Query, QueryContext, QueryFilterFn, QueryGetFn
from orrery.core.event import EventRole, EventRoleType, RoleBinder, RoleList
from orrery.core.status import StatusComponent
from orrery.core.time import SimDateTime
from orrery.utils.relationships import (
    get_relationship,
    get_relationships_with_statuses,
    has_relationship,
    has_relationship_status,
)
from orrery.utils.statuses import has_status


def from_roles(*role_types: EventRoleType) -> RoleBinder:
    """Binds roles using a list of LifeEventRoleTypes"""

    def binder_fn(
        world: World, *args: GameObject, **kwargs: GameObject
    ) -> Optional[RoleList]:
        # It's simpler to not allow users to specify both args and kwargs
        if args and kwargs:
            raise RuntimeError(
                "Cannot specify positional and keyword bindings at the same time"
            )

        roles = RoleList()

        if args:
            binding_queue: List[GameObject] = [*args]
            for role_type in role_types:
                try:
                    candidate = binding_queue.pop(0)
                except IndexError:
                    # Pop throws an index error when the queue is empty
                    candidate = None

                if filled_role := role_type.fill_role(
                    world, roles, candidate=candidate
                ):
                    roles.add(filled_role)  # type: ignore
                else:
                    # Return None if there are no available entities to fill
                    # the current role
                    return None
            return roles

        for role_type in role_types:
            filled_role = role_type.fill_role(
                world, roles, candidate=kwargs.get(role_type.name)
            )
            if filled_role is not None:
                roles.add_role(filled_role)  # type: ignore
            else:
                # Return None if there are no available entities to fill
                # the current role
                return None

        return roles

    return binder_fn


def from_pattern(query: Query) -> RoleBinder:
    """Binds roles using a query pattern"""

    def binder_fn(
        world: World, *args: GameObject, **kwargs: GameObject
    ) -> Optional[RoleList]:
        result_set = query.execute(
            world,
            *[gameobject.uid for gameobject in args],
            **{role_name: gameobject.uid for role_name, gameobject in kwargs.items()},
        )

        if len(result_set):
            chosen_result: Tuple[int, ...] = world.get_resource(random.Random).choice(
                result_set
            )

            return RoleList(
                [
                    EventRole(role, gid)
                    for role, gid in dict(
                        zip(query.get_symbols(), chosen_result)
                    ).items()
                ]
            )

        return None

    return binder_fn


def filter_relationship_stat_gte(
    stat_name: str,
    threshold: float,
    value_type: Literal["raw", "scaled", "norm"] = "raw",
) -> QueryFilterFn:
    """
    Filter function for an ECS query that returns True if the friendship
    value from one character to another is greater than or equal to a given threshold
    """

    def precondition(world: World, *gameobjects: GameObject) -> bool:
        subject, target = gameobjects

        if has_relationship(subject, target):
            relationship = get_relationship(subject, target)
            if value_type == "raw":
                return relationship[stat_name].get_raw_value() >= threshold
            elif value_type == "scaled":
                return relationship[stat_name].get_scaled_value() >= threshold
            elif value_type == "norm":
                return relationship[stat_name].get_normalized_value() >= threshold
            else:
                raise RuntimeError(
                    f"Unknown relationship stat value type, {value_type}"
                )
        return False

    return precondition


def filter_relationship_stat_lte(
    stat_name: str,
    threshold: float,
    value_type: Literal["raw", "scaled", "norm"] = "raw",
) -> QueryFilterFn:
    """
    Filter function for an ECS query that returns True if the friendship
    value from one character to another is greater than or equal to a given threshold
    """

    def precondition(world: World, *gameobjects: GameObject) -> bool:
        subject, target = gameobjects

        if has_relationship(subject, target):
            relationship = get_relationship(subject, target)
            if value_type == "raw":
                return relationship[stat_name].get_raw_value() <= threshold
            elif value_type == "scaled":
                return relationship[stat_name].get_scaled_value() <= threshold
            elif value_type == "norm":
                return relationship[stat_name].get_normalized_value() <= threshold
            else:
                raise RuntimeError(
                    f"Unknown relationship stat value type, {value_type}"
                )
        return False

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


def filter_relationship_has_statuses(
    *status_types: Type[StatusComponent],
) -> QueryFilterFn:
    """
    Query filter function that returns true if the first of the given game
    objects has a relationship toward the second game object with the given
    tags
    """

    def precondition(world: World, *gameobjects: GameObject) -> bool:

        subject, target = gameobjects
        if has_relationship(subject, target):
            return has_relationship_status(subject, target, *status_types)

        return False

    return precondition


def find_relationships_with_statuses(
    *status_types: Type[StatusComponent],
) -> QueryGetFn:
    """
    Returns a list of all the GameObjects with the given component
    """

    def fn(ctx: QueryContext, world: World, *variables: str) -> List[Tuple[int, ...]]:
        if ctx.relation is None:
            raise TypeError("Relation is None inside query")

        results: List[Tuple[int, ...]] = []
        subject_id: int
        for (subject_id,) in ctx.relation.get_as_tuple(slice(0, -1), variables[0]):
            subject = world.get_gameobject(subject_id)
            for r in get_relationships_with_statuses(subject, *status_types):
                results.append((subject_id, r.target))

        return results

    return fn


def life_stage_eq(stage: LifeStage) -> QueryFilterFn:
    def fn(world: World, *gameobjects: GameObject) -> bool:
        character = gameobjects[0].try_component(GameCharacter)
        if character is not None:
            return character.life_stage == stage
        return False

    return fn


def life_stage_ge(stage: LifeStage) -> QueryFilterFn:
    def fn(world: World, *gameobjects: GameObject) -> bool:
        character = gameobjects[0].try_component(GameCharacter)
        if character is not None:
            return character.life_stage >= stage
        return False

    return fn


def life_stage_le(stage: LifeStage) -> QueryFilterFn:
    def fn(world: World, *gameobjects: GameObject) -> bool:
        character = gameobjects[0].try_component(GameCharacter)
        if character is not None:
            return character.life_stage <= stage
        return False

    return fn


def over_age(age: int) -> QueryFilterFn:
    def fn(world: World, *gameobjects: GameObject) -> bool:
        character = gameobjects[0].try_component(GameCharacter)
        if character is not None:
            return character.age > age
        return False

    return fn


def is_single(world: World, *gameobjects: GameObject) -> bool:
    """Return True if this entity has no relationships tagged as significant others"""
    return len([get_relationships_with_statuses(gameobjects[0], Married, Dating)]) == 0


def before_year(year: int) -> QueryFilterFn:
    """Return precondition function that checks if the date is before a given year"""

    def fn(world: World, *gameobjects: GameObject) -> bool:
        return world.get_resource(SimDateTime).year < year

    return fn


def after_year(year: int) -> QueryFilterFn:
    """Return precondition function that checks if the date is after a given year"""

    def fn(world: World, *gameobjects: GameObject) -> bool:
        return world.get_resource(SimDateTime).year > year

    return fn


def is_gender(gender: Gender) -> QueryFilterFn:
    """Return precondition function that checks if an entity is a given gender"""

    def fn(world: World, *gameobjects: GameObject) -> bool:
        if character := gameobjects[0].try_component(GameCharacter):
            return character.gender == gender
        return False

    return fn


def has_work_experience_filter(
    occupation_type: str, years_experience: int = 0
) -> QueryFilterFn:
    """
    Returns Precondition function that returns true if the entity
    has experience as a given occupation type.

    Parameters
    ----------
    occupation_type: str
        The name of the occupation to check for
    years_experience: int
        The number of years of experience the entity needs to have

    Returns
    -------
    QueryFilterFn
        The precondition function used when filling the occupation
    """

    def fn(world: World, *gameobjects: GameObject) -> bool:
        total_experience: float = 0
        gameobject = gameobjects[0]

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


def has_status_filter(status_type: Type[StatusComponent]) -> QueryFilterFn:
    """Check if a GameObject has the given status present"""

    def filter_fn(world: World, *gameobject: GameObject) -> bool:
        return has_status(gameobject[0], status_type)

    return filter_fn


def has_component_filter(component_type: Type[Component]) -> QueryFilterFn:
    """Return True if the entity has a given component type"""

    def precondition(world: World, *gameobject: GameObject) -> bool:
        return gameobject[0].has_component(component_type)

    return precondition
