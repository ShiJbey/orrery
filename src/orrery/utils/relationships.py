from __future__ import annotations

from typing import List, Type, TypeVar

from orrery.core.config import OrreryConfig
from orrery.core.ecs import Component, GameObject
from orrery.core.relationship import (
    Relationship,
    RelationshipManager,
    RelationshipNotFound,
    RelationshipStat,
)
from orrery.core.social_rule import SocialRuleLibrary
from orrery.core.status import StatusManager
from orrery.utils.statuses import add_status, has_status, remove_status

_RST = TypeVar("_RST", bound="RelationshipStatus")


def add_relationship(subject: GameObject, target: GameObject) -> GameObject:
    """
    Creates a new relationship from the subject to the target

    Parameters
    ----------
    subject: GameObject
        The GameObject that owns the relationship
    target: GameObject
        The GameObject that the Relationship is directed toward

    Returns
    -------
    Relationship
        The new relationship instance
    """
    world = subject.world
    schema = world.get_resource(OrreryConfig).relationship_schema

    relationship = world.spawn_gameobject(
        [
            Relationship(
                target=target.uid,
                stats={
                    name: RelationshipStat(
                        min_value=config.min_value,
                        max_value=config.max_value,
                        changes_with_time=config.changes_with_time,
                    )
                    for name, config in schema.stats.items()
                },
            ),
            StatusManager(),
        ]
    )

    subject.get_component(RelationshipManager).relationships[
        target.uid
    ] = relationship.uid

    subject.add_child(relationship)

    social_rules = subject.world.get_resource(SocialRuleLibrary).get_active_rules()

    for rule in social_rules:
        if rule.check_preconditions(subject.world, subject, target):
            rule.activate(subject.world, subject, target, relationship)

    return relationship


def get_relationship(
    subject: GameObject,
    target: GameObject,
    create_new: bool = False,
) -> Relationship:
    """
    Get a relationship toward another entity

    Parameters
    ----------
    subject: GameObject
        The owner of the relationship
    target: GameObject
        The character the relationship is directed toward
    create_new: bool (default: False)
        Create a new relationship if one does not already exist

    Returns
    -------
    Relationship
        The relationship instance toward the other entity

    Throws
    ------
    KeyError
        If no relationship is found for the given target and create_new is False
    """
    try:
        world = subject.world
        relationship_id = subject.get_component(RelationshipManager).relationships[
            target.uid
        ]
        return world.get_gameobject(relationship_id).get_component(Relationship)
    except KeyError:
        if create_new:
            return add_relationship(subject, target).get_component(Relationship)
        else:
            raise RelationshipNotFound(subject.name, target.name)


def has_relationship(subject: GameObject, target: GameObject) -> bool:
    """Check if there is an existing relationship from the subject to the target

    Parameters
    ----------
    subject: GameObject
        The GameObject to check for a relationship instance on
    target: GameObject
        The GameObject to check is the target of an existing relationship instance

    Returns
    -------
    bool
        Returns True if there is an existing Relationship instance with the
        target as the target
    """
    return target.uid in subject.get_component(RelationshipManager)


def add_relationship_status(
    subject: GameObject, target: GameObject, status: Component
) -> None:
    """
    Add a relationship status to the given character

    Parameters
    ----------
    subject: GameObject
        The character to add the relationship status to
    target: GameObject
        The character the relationship status is directed toward
    status: Status
        The core component of the status
    """
    relationship = get_relationship(subject, target, create_new=True)
    add_status(relationship.gameobject, status)


def get_relationship_status(
    subject: GameObject,
    target: GameObject,
    status_type: Type[_RST],
) -> _RST:
    """
    Get a relationship status from the subject to the target
    of a given type

    Parameters
    ----------
    subject: GameObject
        The character to add the relationship status to
    target: GameObject
        The character that is the target of the status
    status_type: Type[RelationshipStatus]
        The type of the status
    """
    return get_relationship(subject, target, create_new=True).gameobject.get_component(
        status_type
    )


def remove_relationship_status(
    subject: GameObject,
    target: GameObject,
    status_type: Type[Component],
) -> None:
    """
    Remove a relationship status to the given character

    Parameters
    ----------
    subject: GameObject
        The character to add the relationship status to
    target: GameObject
        The character that is the target of the status
    status_type: Type[RelationshipStatus]
        The type of the relationship status to remove
    """
    relationship = get_relationship(subject, target, create_new=True)
    remove_status(relationship.gameobject, status_type)


def has_relationship_status(
    subject: GameObject,
    target: GameObject,
    *status_type: Type[Component],
) -> bool:
    """
    Check if a relationship between characters has a certain status type

    Parameters
    ----------
    subject: GameObject
        The character to add the relationship status to
    target: GameObject
        The character that is the target of the status
    status_type: Type[RelationshipStatus]
        The type of the relationship status to remove

    Returns
    -------
        Returns True if relationship has a given status
    """
    relationship = get_relationship(subject, target, create_new=True)
    return all([has_status(relationship.gameobject, s) for s in status_type])


def get_relationships_with_statuses(
    subject: GameObject, *status_types: Type[Component]
) -> List[Relationship]:
    """Get all the relationships with the given status types

    Parameters
    ----------
    subject: GameObject
        The character to check for relationships on
    *status_types: Type[Component]
        Status types to check for on relationship instances

    Returns
    -------
    List[Relationship]
        Relationships with the given status types
    """
    world = subject.world
    relationship_manager = subject.get_component(RelationshipManager)
    matches: List[Relationship] = []
    for target_id, rel_id in relationship_manager.relationships.items():
        relationship = world.get_gameobject(rel_id)
        target = world.get_gameobject(target_id)
        if has_relationship_status(subject, target, *status_types):
            matches.append(relationship.get_component(Relationship))
    return matches
