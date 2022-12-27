import json
from typing import Any, Dict, List, Optional, Tuple, Type

from orrery.activity import Activity, ActivityLibrary, ActivityManager, LikedActivities
from orrery.components.shared import Location, FrequentedLocations
from orrery.ecs import Component, ComponentBundle, World, GameObject
from orrery.config import ActivityToVirtueConfig, OrreryConfig
from orrery.relationship import (
    Relationship,
    RelationshipManager,
    RelationshipNotFound,
    RelationshipStat,
)
from orrery.social_rule import SocialRuleLibrary
from orrery.traits import Trait, TraitManager
from orrery.virtues import VirtueVector


def add_relationship(
    world: World, subject: GameObject, target: GameObject
) -> Relationship:
    """Adds a new entity to the relationship manager and returns the new relationship between the two"""
    schema = world.get_resource(OrreryConfig).relationship_schema

    relationship = Relationship(
        {
            name: RelationshipStat(
                min_value=config.min_value,
                max_value=config.max_value,
                changes_with_time=config.changes_with_time,
            )
            for name, config in schema.stats.items()
        }
    )

    social_rules = world.get_resource(SocialRuleLibrary).get_active_rules()

    for rule in social_rules:
        if rule.check_preconditions(world, subject, target):
            rule.activate(world, subject, target, relationship)

    for trait in subject.get_component(TraitManager):
        for rule in trait.rules:
            if rule.check_preconditions(world, subject, target):
                rule.activate(world, subject, target, relationship)

    subject.get_component(RelationshipManager).add(target.id, relationship)

    return relationship


def get_relationship(
    world: World,
    subject: GameObject,
    target: GameObject,
    create_new: bool = False,
) -> Relationship:
    """
    Get a relationship toward another entity

    Parameters
    ----------
    target: int
        Unique identifier of the other entity
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
        return subject.get_component(RelationshipManager).get(target.id)
    except KeyError:
        if create_new:
            return add_relationship(world, subject, target)
        else:
            raise RelationshipNotFound(subject.name, target.name)


def add_trait(world: World, character: GameObject, trait: Trait) -> None:
    character.get_component(TraitManager).add_trait(trait)
    for other_id, relationship in character.get_component(RelationshipManager):
        other = world.get_gameobject(other_id)
        for rule in trait.rules:
            if rule.check_preconditions(world, character, other):
                rule.activate(world, character, other, relationship)


def remove_trait(character: GameObject, trait_name: str) -> None:
    if trait := character.get_component(TraitManager).get_trait(trait_name):
        character.get_component(TraitManager).remove_trait(trait_name)
        for _, relationship in character.get_component(RelationshipManager):
            for rule in trait.rules:
                rule.deactivate(relationship)


def has_trait(character: GameObject, trait_name: str) -> bool:
    return trait_name in character.get_component(TraitManager)


def set_liked_activities(world: World, character: GameObject, n: int = 3) -> None:

    scores: List[Tuple[float, Activity]] = []

    activities_to_virtues = world.get_resource(ActivityToVirtueConfig)

    virtue_vect = character.get_component(VirtueVector)

    for activity in world.get_resource(ActivityLibrary):
        activity_virtues = activities_to_virtues.mappings.get(activity, VirtueVector())
        score = virtue_vect.compatibility(activity_virtues)
        scores.append((score, activity))

    liked_activities = LikedActivities(
        set(
            [
                activity_score[1]
                for activity_score in sorted(scores, key=lambda s: s[0], reverse=True)
            ][:n]
        )
    )

    character.add_component(liked_activities)


def find_places_with_activities(world: World, *activities: str) -> List[int]:
    """Return a list of entity ID for locations that have the given activities"""
    locations = world.get_component(ActivityManager)
    activity_library = world.get_resource(ActivityLibrary)

    matches: List[int] = []

    activity_instances = [activity_library.get(a, create_new=False) for a in activities]

    for location_id, location in locations:
        if all([a in location for a in activity_instances]):
            matches.append(location_id)

    return matches


def find_places_with_any_activities(world: World, *activities: str) -> List[int]:
    """Return a list of entity ID for locations that have any of the given activities
    Results are sorted by how many activities they match
    """
    locations = world.get_component(ActivityManager)
    activity_library = world.get_resource(ActivityLibrary)

    activity_instances = [activity_library.get(a, create_new=False) for a in activities]

    def score_location(location: ActivityManager) -> int:
        location_score: int = 0
        for activity in activity_instances:
            if activity in location:
                location_score += 1
        return location_score

    locations = world.get_component(ActivityManager)

    matches: List[Tuple[int, int]] = []

    for location_id, location in locations:
        score = score_location(location)
        if score > 0:
            matches.append((score, location_id))

    return [match[1] for match in sorted(matches, key=lambda m: m[0], reverse=True)]


def set_frequented_locations(world: World, character: GameObject, n: int = 3) -> None:
    # Find locations in the town and select n to be places that the
    # given character frequents
    liked_activities = [
        a.name for a in character.get_component(LikedActivities).activities
    ]

    locations = find_places_with_any_activities(world, *list(liked_activities))

    n_locations_to_select = min(n, len(locations))

    selected_locations = locations[:n_locations_to_select]

    character.add_component(FrequentedLocations(set(selected_locations)))

    for l in selected_locations:
        world.get_gameobject(l).get_component(Location).frequented_by.add(character.id)


def pprint_gameobject(gameobject: GameObject) -> None:
    print(
        json.dumps(
            gameobject.to_dict(),
            sort_keys=True,
            indent=2,
        )
    )


def add_character(
    world: World,
    bundle: ComponentBundle,
    overrides: Optional[Dict[Type[Component], Dict[str, Any]]] = None,
) -> GameObject:
    character = bundle.spawn(world, overrides)
    set_liked_activities(world, character)
    set_frequented_locations(world, character)
    return character


def add_location(
    world: World,
    bundle: ComponentBundle,
    overrides: Optional[Dict[Type[Component], Dict[str, Any]]] = None,
) -> GameObject:
    location = bundle.spawn(world, overrides)
    return location


def add_relationship_status(
    world: World, character: GameObject, status_bundle: ComponentBundle
) -> None:
    """Add a status to the character"""
    status = status_bundle.spawn(world)
    character.add_child(status)
