from __future__ import annotations

import random
from typing import List, Optional, Tuple, Type

from orrery.components.business import Occupation, WorkHistory
from orrery.components.character import GameCharacter, Gender, LifeStage
from orrery.core.ecs import Component, GameObject, World
from orrery.core.event import EventRole, EventRoleType, RoleBinder, RoleList
from orrery.core.query import Query, QueryContext, QueryFilterFn, QueryGetFn
from orrery.core.relationship import RelationshipManager, RelationshipTag
from orrery.core.status import Status
from orrery.core.time import SimDateTime
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


def friendship_gte(threshold: float) -> QueryFilterFn:
    """
    Filter function for an ECS query that returns True if the friendship
    value from one character to another is greater than or equal to a given threshold
    """

    def precondition(world: World, *gameobjects: GameObject) -> bool:
        if relationships := gameobjects[0].try_component(RelationshipManager):
            return (
                gameobjects[1].uid in relationships
                and relationships.get(gameobjects[1].uid)[
                    "Friendship"
                ].get_normalized_value()
                >= threshold
            )
        return False

    return precondition


def friendship_lte(threshold: float) -> QueryFilterFn:
    """
    Filter function for an ECS query that returns True if the friendship
    value from one character to another is less than or equal to a given threshold
    """

    def precondition(world: World, *gameobjects: GameObject) -> bool:
        if relationships := gameobjects[0].try_component(RelationshipManager):
            return (
                gameobjects[1].uid in relationships
                and relationships.get(gameobjects[1].uid)[
                    "Friendship"
                ].get_normalized_value()
                <= threshold
            )
        return False

    return precondition


def romance_gte(threshold: float) -> QueryFilterFn:
    """
    Filter function for an ECS query that returns True if the romance
    value from one character to another is greater than or equal to a given threshold
    """

    def precondition(world: World, *gameobjects: GameObject) -> bool:
        if relationships := gameobjects[0].try_component(RelationshipManager):
            return (
                gameobjects[1].uid in relationships
                and relationships.get(gameobjects[1].uid)[
                    "Romance"
                ].get_normalized_value()
                >= threshold
            )
        return False

    return precondition


def romance_lte(threshold: float) -> QueryFilterFn:
    """
    Filter function for an ECS query that returns True if the romance
    value from one character to another is less than or equal to a given threshold
    """

    def precondition(world: World, *gameobjects: GameObject) -> bool:
        if relationships := gameobjects[0].try_component(RelationshipManager):
            return (
                gameobjects[1].uid in relationships
                and relationships.get(gameobjects[1].uid)[
                    "Romance"
                ].get_normalized_value()
                <= threshold
            )
        return False

    return precondition


def get_friendships_gte(threshold: float) -> QueryGetFn:
    """
    Returns QueryGetFn that finds all the relationships of the first variable that have
    friendship scores greater than or equal to the threshold and binds them to the
    second variable
    """

    def clause(
        ctx: QueryContext, world: World, *variables: str
    ) -> List[Tuple[int, ...]]:
        # loop through each row in the ctx at the given column
        results: List[Tuple[int, ...]] = []
        for (subject,) in ctx.relation.get_as_tuple(slice(0, -1), variables[0]):  # type: ignore
            gameobject = world.get_gameobject(subject)  # type: ignore
            for r in gameobject.get_component(RelationshipManager):
                if r["Friendship"].get_normalized_value() >= threshold:
                    results.append((subject, r.target))  # type: ignore

        return results

    return clause


def get_friendships_lte(threshold: float) -> QueryGetFn:
    """
    Returns QueryGetFn that finds all the relationships of the first variable that have
    friendship scores less than or equal to the threshold and binds them to the
    second variable
    """

    def clause(
        ctx: QueryContext, world: World, *variables: str
    ) -> List[Tuple[int, ...]]:
        results: List[Tuple[int, ...]] = []
        for (subject,) in ctx.relation.get_as_tuple(slice(0, -1), variables[0]):  # type: ignore
            gameobject = world.get_gameobject(subject)  # type: ignore
            for r in gameobject.get_component(RelationshipManager):
                if r["Friendship"].get_normalized_value() <= threshold:
                    results.append((subject, r.target))  # type: ignore

        return results

    return clause


def get_romances_gte(threshold: float) -> QueryGetFn:
    """
    Returns QueryGetFn that finds all the relationships of the first variable that have
    romance scores greater than or equal to the threshold and binds them to the
    second variable
    """

    def clause(
        ctx: QueryContext, world: World, *variables: str
    ) -> List[Tuple[int, ...]]:
        results: List[Tuple[int, ...]] = []
        for (subject,) in ctx.relation.get_as_tuple(slice(0, -1), variables[0]):
            gameobject = world.get_gameobject(subject)
            for r in gameobject.get_component(RelationshipManager):
                if r["Romance"].get_normalized_value() >= threshold:
                    results.append((subject, r.target))

        return results

    return clause


def get_romances_lte(threshold: float) -> QueryGetFn:
    """
    Returns QueryGetFn that finds all the relationships of the first variable that have
    romance scores less than or equal to the threshold and binds them to the
    second variable
    """

    def clause(
        ctx: QueryContext, world: World, *variables: str
    ) -> List[Tuple[int, ...]]:
        results: List[Tuple[int, ...]] = []
        for (subject,) in ctx.relation.get_as_tuple(slice(0, -1), variables[0]):  # type: ignore
            gameobject = world.get_gameobject(subject)  # type: ignore
            for r in gameobject.get_component(RelationshipManager):
                if r["Romance"].get_normalized_value() <= threshold:
                    results.append((subject, r.target))  # type: ignore

        return results

    return clause


def relationship_has_tags(tags: RelationshipTag) -> QueryFilterFn:
    """
    Query filter function that returns true if the first of the given game
    objects has a relationship toward the second game object with the given
    tags
    """

    def precondition(world: World, *gameobjects: GameObject) -> bool:

        subject, target = gameobjects
        relationships = subject.get_component(RelationshipManager)
        if target.uid in relationships:
            return tags in relationships.get(target.uid).tags
        else:
            return False

    return precondition


def get_relationships_with_tags(tags: RelationshipTag) -> QueryGetFn:
    """
    Returns a list of all the GameObjects with the given component
    """

    def fn(ctx: QueryContext, world: World, *variables: str) -> List[Tuple[int, ...]]:
        results: List[Tuple[int, ...]] = []
        for (subject,) in ctx.relation.get_as_tuple(slice(0, -1), variables[0]):  # type: ignore
            gameobject = world.get_gameobject(subject)  # type: ignore
            for r in gameobject.get_component(RelationshipManager):
                if tags in r.tags:
                    results.append((subject, r.target))  # type: ignore

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
    return (
        len(
            [
                r
                for _, r in gameobjects[0].get_component(RelationshipManager)
                if RelationshipTag.SignificantOther in r.tags
            ]
        )
        == 0
    )


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


def has_any_work_experience(world: World, *gameobjects: GameObject) -> bool:
    """Return True if the entity has any work experience at all"""
    return len(gameobjects[0].get_component(WorkHistory)) > 0


def has_experience_as_a(
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


def has_status_filter(status_type: Type[Status]) -> QueryFilterFn:
    """Check if a GameObject has the given status present"""

    def filter_fn(world: World, *gameobject: GameObject) -> bool:
        return has_status(gameobject[0], status_type)

    return filter_fn


def has_component_filter(component_type: Type[Component]) -> QueryFilterFn:
    """Return True if the entity has a given component type"""

    def precondition(world: World, *gameobject: GameObject) -> bool:
        return gameobject[0].has_component(component_type)

    return precondition
