from __future__ import annotations

from typing import Type, TypeVar

from orrery.core.config import OrreryConfig
from orrery.core.ecs import GameObject
from orrery.core.relationship import (
    Relationship,
    RelationshipManager,
    RelationshipNotFound,
    RelationshipStat,
    RelationshipStatus,
)
from orrery.core.social_rule import SocialRuleLibrary

_RST = TypeVar("_RST", bound="RelationshipStatus")


def add_relationship(subject: GameObject, target: GameObject) -> Relationship:
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
    schema = subject.world.get_resource(OrreryConfig).relationship_schema

    relationship = Relationship(
        target=target.uid,
        stats={
            name: RelationshipStat(
                min_value=config.min_value,
                max_value=config.max_value,
                changes_with_time=config.changes_with_time,
            )
            for name, config in schema.stats.items()
        },
    )

    social_rules = subject.world.get_resource(SocialRuleLibrary).get_active_rules()

    for rule in social_rules:
        if rule.check_preconditions(subject.world, subject, target):
            rule.activate(subject.world, subject, target, relationship)

    subject.get_component(RelationshipManager).add(target.uid, relationship)

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
        return subject.get_component(RelationshipManager).get(target.uid)
    except KeyError:
        if create_new:
            return add_relationship(subject, target)
        else:
            raise RelationshipNotFound(subject.name, target.name)


def add_relationship_status(
    subject: GameObject, target: GameObject, status: RelationshipStatus
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
    relationship.add_status(subject, status)


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
    return get_relationship(subject, target, create_new=True).get_status(status_type)


def remove_relationship_status(
    subject: GameObject,
    target: GameObject,
    status_type: Type[RelationshipStatus],
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
    relationship.remove_status(subject, status_type)


def has_relationship_status(
    subject: GameObject,
    target: GameObject,
    status_type: Type[RelationshipStatus],
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
    return get_relationship(subject, target, create_new=True).has_status(status_type)
