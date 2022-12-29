import json
import random
from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar

import orrery.events
from orrery.components.business import (
    Business,
    ClosedForBusiness,
    InTheWorkforce,
    Occupation,
    OccupationType,
    OpenForBusiness,
    Services,
    ServiceTypes,
    Unemployed,
    WorkHistory,
    unemployed_status,
)
from orrery.components.character import CharacterLibrary, GameCharacter, LifeStage
from orrery.components.residence import (
    Residence,
    ResidenceComponentBundle,
    Resident,
    Vacant,
)
from orrery.components.shared import (
    Active,
    Building,
    FrequentedLocations,
    Location,
    Name,
    Position2D,
)
from orrery.core.activity import (
    Activity,
    ActivityLibrary,
    ActivityManager,
    ActivityToVirtueMap,
    LikedActivities,
)
from orrery.core.config import OrreryConfig
from orrery.core.ecs import Component, ComponentBundle, GameObject, World
from orrery.core.event import EventLog
from orrery.core.query import QueryBuilder
from orrery.core.relationship import (
    Relationship,
    RelationshipManager,
    RelationshipNotFound,
    RelationshipStat,
    RelationshipTag,
)
from orrery.core.settlement import Settlement, create_grid_settlement
from orrery.core.social_rule import SocialRuleLibrary
from orrery.core.status import Status, StatusManager
from orrery.core.time import SimDateTime
from orrery.core.tracery import Tracery
from orrery.core.traits import Trait, TraitManager
from orrery.core.virtues import VirtueVector
from orrery.utils.query import is_unemployed

_CT = TypeVar("_CT", bound=Component)


def create_settlement(
    world: World,
    settlement_name: str = "#settlement_name#",
    settlement_size: Tuple[int, int] = (5, 5),
) -> GameObject:
    """Create a new Settlement to represent the Town"""
    generated_name = world.get_resource(Tracery).generate(settlement_name)
    settlement = world.spawn_gameobject(
        [create_grid_settlement(generated_name, settlement_size)]
    )
    return settlement


def create_character(
    world: World,
    bundle: ComponentBundle,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    age: Optional[int] = None,
    life_stage: Optional[LifeStage] = None,
    gender: Optional[str] = None,
) -> GameObject:
    overrides: Dict[Type[Component], Dict[str, Any]] = {GameCharacter: {}}

    if first_name:
        overrides[GameCharacter]["first_name"] = first_name

    if last_name:
        overrides[GameCharacter]["last_name"] = last_name

    if age:
        overrides[GameCharacter]["age"] = age

    if life_stage:
        overrides[GameCharacter]["life_stage"] = life_stage

    if gender:
        overrides[GameCharacter]["gender"] = gender

    return bundle.spawn(world, overrides=overrides)


def create_business(
    world: World,
    bundle: ComponentBundle,
    name: Optional[str] = None,
) -> GameObject:
    overrides: Dict[Type[Component], Dict[str, Any]] = {Business: {}}

    if name:
        overrides[Business]["name"] = name

    return bundle.spawn(world, overrides=overrides)


def create_residence(
    world: World,
    bundle: ResidenceComponentBundle,
    settlement: int,
    name: Optional[str] = None,
) -> GameObject:
    overrides: Dict[Type[Component], Dict[str, Any]] = {Name: {"name": "residence"}}

    if name:
        overrides[Business]["name"] = name

    overrides[Residence] = {"settlement": settlement}

    return bundle.spawn(world, overrides=overrides)


def add_business(
    world: World,
    business: GameObject,
    settlement: GameObject,
    lot: Optional[int] = None,
) -> GameObject:
    settlement_comp = settlement.get_component(Settlement)

    # Increase the count of this business type in the settlement
    settlement_comp.business_counts[business.get_component(Business).config.name] += 1

    if lot is None:
        lot = settlement_comp.land_map.get_vacant_lots()[0]

    # Reserve the space
    settlement_comp.land_map.reserve_lot(lot, business.id)

    # Set the position of the building
    position = settlement_comp.land_map.get_lot_position(lot)
    business.get_component(Position2D).x = position[0]
    business.get_component(Position2D).y = position[1]

    # Give the business a building
    business.add_component(
        Building(building_type="commercial", lot=lot, settlement=settlement.id)
    )
    business.add_component(OpenForBusiness())
    business.add_component(Active())

    return business


def add_residence(
    world: World, residence: GameObject, settlement: GameObject, lot: int
) -> GameObject:
    settlement_comp = settlement.get_component(Settlement)

    # Reserve the space
    settlement_comp.land_map.reserve_lot(lot, residence.id)

    # Set the position of the building
    position = settlement_comp.land_map.get_lot_position(lot)
    residence.get_component(Position2D).x = position[0]
    residence.get_component(Position2D).y = position[1]

    # Give the business a building
    residence.add_component(
        Building(building_type="residential", lot=lot, settlement=settlement.id)
    )
    residence.add_component(Vacant())
    residence.add_component(Active())

    return residence


def generate_child_bundle(
    world: World, parent_a: GameObject, parent_b: GameObject
) -> ComponentBundle:
    rng = world.get_resource(random.Random)
    library = world.get_resource(CharacterLibrary)

    eligible_child_configs = [
        *parent_a.get_component(GameCharacter).config.spawning.child_archetypes,
        *parent_b.get_component(GameCharacter).config.spawning.child_archetypes,
    ]

    potential_child_bundles = library.get_matching_bundles(*eligible_child_configs)

    if potential_child_bundles:

        bundle = rng.choice(potential_child_bundles)

        return bundle

    else:
        config_to_inherit = rng.choice(
            [
                parent_a.get_component(GameCharacter).config,
                parent_b.get_component(GameCharacter).config,
            ]
        )

        bundle = library.get_bundle(config_to_inherit.name)

        return bundle

    return child


def demolish_building(world: World, gameobject: GameObject) -> None:
    """Remove the building component and free the land grid space"""
    building = gameobject.get_component(Building)
    settlement = world.get_gameobject(building.settlement).get_component(Settlement)
    settlement.land_map.free_lot(gameobject.get_component(Building).lot)
    gameobject.remove_component(Building)
    gameobject.remove_component(Position2D)


def set_residence(
    world: World,
    character: GameObject,
    new_residence: Optional[GameObject],
    is_owner: bool = False,
) -> None:
    """
    Moves a character into a new permanent residence
    """
    if resident := character.try_component(Resident):
        # This character is currently a resident at another location
        former_residence = world.get_gameobject(resident.residence).get_component(
            Residence
        )

        if former_residence.is_owner(character.id):
            former_residence.remove_owner(character.id)

        former_residence.remove_resident(character.id)
        character.remove_component(Resident)

        former_settlement = world.get_gameobject(resident.settlement).get_component(
            Settlement
        )
        former_settlement.decrement_population()

        if len(former_residence.residents) <= 0:
            former_residence.gameobject.add_component(Vacant())

    if new_residence is None:
        return

    # Move into new residence
    new_residence.get_component(Residence).add_resident(character.id)
    new_settlement = world.get_gameobject(
        new_residence.get_component(Residence).settlement
    )

    if is_owner:
        new_residence.get_component(Residence).add_owner(character.id)

    character.add_component(
        Resident(residence=new_residence.id, settlement=new_settlement.id)
    )

    if new_residence.has_component(Vacant):
        new_residence.remove_component(Vacant)

    new_settlement.get_component(Settlement).increment_population()


def check_share_residence(gameobject: GameObject, other: GameObject) -> bool:
    resident_comp = gameobject.try_component(Resident)
    other_resident_comp = other.try_component(Resident)

    return (
        resident_comp is not None
        and other_resident_comp is not None
        and resident_comp.residence == other_resident_comp.residence
    )


def depart_town(world: World, character: GameObject, reason: str = "") -> None:
    """
    Helper function that handles all the core logistics of moving someone
    out of the town
    """

    residence = world.get_gameobject(
        character.get_component(Resident).residence
    ).get_component(Residence)

    set_residence(world, character, None)
    departing_characters: List[GameObject] = [character]

    # Get people that this character lives with and have them depart with their
    # spouse(s) and children. This function may need to be refactored in the future
    # to perform BFS on the relationship tree when moving out extended families living
    # within the same residence
    for resident_id in residence.residents:
        resident = world.get_gameobject(resident_id)

        if resident == character:
            continue

        if (
            RelationshipTag.Spouse
            in character.get_component(RelationshipManager).get(resident_id).tags
        ):
            set_residence(world, resident, None)
            departing_characters.append(resident)

        elif (
            RelationshipTag.Child
            in character.get_component(RelationshipManager).get(resident_id).tags
        ):
            set_residence(world, resident, None)
            departing_characters.append(resident)

    world.get_resource(EventLog).record_event(
        orrery.events.DepartEvent(
            date=world.get_resource(SimDateTime),
            characters=departing_characters,
            reason=reason,
        )
    )


def add_coworkers(world: World, character: GameObject, business: GameObject) -> None:
    """Add coworker tags to current coworkers in relationship network"""
    for employee_id in business.get_component(Business).get_employees():
        if employee_id == character.id:
            continue

        coworker = world.get_gameobject(employee_id)

        character.get_component(RelationshipManager).get(employee_id).add_tags(
            RelationshipTag.Coworker
        )

        coworker.get_component(RelationshipManager).get(character.id).add_tags(
            RelationshipTag.Coworker
        )


def remove_coworkers(world: World, character: GameObject, business: GameObject) -> None:
    """Remove coworker tags from current coworkers in relationship network"""
    for employee_id in business.get_component(Business).get_employees():
        if employee_id == character.id:
            continue

        coworker = world.get_gameobject(employee_id)

        character.get_component(RelationshipManager).get(employee_id).remove_tags(
            RelationshipTag.Coworker
        )

        coworker.get_component(RelationshipManager).get(character.id).remove_tags(
            RelationshipTag.Coworker
        )


def shutdown_business(world: World, business: GameObject) -> None:
    """Close a business and remove all employees and the owner"""
    date = world.get_resource(SimDateTime)

    event = orrery.events.BusinessClosedEvent(date, business)

    business.remove_component(OpenForBusiness)
    business.add_component(ClosedForBusiness())

    world.get_resource(EventLog).record_event(event)

    business_comp = business.get_component(Business)

    for employee in business_comp.get_employees():
        end_job(world, world.get_gameobject(employee), reason=event.name)

    if business_comp.owner_type is not None and business_comp.owner is not None:
        end_job(world, world.get_gameobject(business_comp.owner), reason=event.name)

    business.remove_component(Active)
    business.remove_component(Location)
    demolish_building(world, business)


def start_job(
    world: World,
    business: Business,
    character: GameObject,
    occupation: Occupation,
    is_owner: bool = False,
) -> None:
    if is_owner:
        business.owner = character.id

    business.add_employee(character.id, occupation.occupation_type)
    character.add_component(occupation)

    add_coworkers(world, character, business.gameobject)

    if has_status(character, Unemployed):
        status = get_status(world, character, Unemployed)
        remove_status(character, status)


def end_job(
    world: World,
    character: GameObject,
    reason: str,
) -> None:
    occupation = character.get_component(Occupation)
    business = world.get_gameobject(occupation.business)
    business_comp = business.get_component(Business)

    # Update the former employees RelationshipManager
    remove_coworkers(world, character, business)

    if business_comp.owner_type is not None and business_comp.owner == character.id:
        business_comp.set_owner(None)

    business_comp.remove_employee(character.id)

    character.remove_component(Occupation)
    add_status(world, character, unemployed_status(336))

    # Update the former employee's work history
    if not character.has_component(WorkHistory):
        character.add_component(WorkHistory())

    character.get_component(WorkHistory).add_entry(
        occupation_type=occupation.occupation_type,
        business=business.id,
        years_held=occupation.years_held,
    )

    # Emit the event
    world.get_resource(EventLog).record_event(
        orrery.events.EndJobEvent(
            date=world.get_resource(SimDateTime),
            character=character,
            business=business,
            occupation=occupation.occupation_type,
            reason=reason,
        )
    )


def find_places_with_services(world: World, *services: str) -> List[int]:
    """
    Get all the active locations with the given services

    Parameters
    ----------
    world: World
        The world instance to search within

    services: Tuple[str]
        The services to search for

    Returns
    -------
    The IDs of the matching entities
    """
    matches: List[int] = []
    for gid, services_component in world.get_component(Services):
        if all([services_component.has_service(ServiceTypes.get(s)) for s in services]):
            matches.append(gid)
    return matches


def fill_open_position(
    world: World,
    occupation_type: OccupationType,
    business: Business,
    rng: random.Random,
    candidate: Optional[GameObject] = None,
) -> Optional[Tuple[GameObject, Occupation]]:
    """
    Attempt to find a component entity that meets the preconditions
    for this occupation
    """
    query_builder = (
        QueryBuilder().with_((InTheWorkforce, Active)).filter_(is_unemployed)
    )

    if occupation_type.precondition:
        query_builder.filter_(occupation_type.precondition)

    q = query_builder.build()

    if candidate:
        candidate_list = q.execute(world, Candidate=candidate.id)
    else:
        candidate_list = q.execute(world)

    if candidate_list:
        chosen_candidate = world.get_gameobject(rng.choice(candidate_list)[0])
        return chosen_candidate, Occupation(
            occupation_type=occupation_type.name,
            business=business.gameobject.id,
            level=occupation_type.level,
        )

    return None


def add_relationship(
    world: World, subject: GameObject, target: GameObject
) -> Relationship:
    """Adds a new entity to the relationship manager and returns the new relationship between the two"""
    schema = world.get_resource(OrreryConfig).relationship_schema

    relationship = Relationship(
        target=target.id,
        stats={
            name: RelationshipStat(
                min_value=config.min_value,
                max_value=config.max_value,
                changes_with_time=config.changes_with_time,
            )
            for name, config in schema.stats.items()
        },
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

    activities_to_virtues = world.get_resource(ActivityToVirtueMap)

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


def add_character(world: World, character: GameObject) -> GameObject:
    set_liked_activities(world, character)
    set_frequented_locations(world, character)
    character.add_component(Active())

    character_comp = character.get_component(GameCharacter)

    if character_comp.life_stage >= LifeStage.YoungAdult:
        character.add_component(InTheWorkforce())
        add_status(world, character, unemployed_status(336))

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


def add_status(world: World, gameobject: GameObject, bundle: ComponentBundle) -> None:
    """Adds a new status to the given GameObject"""
    status = bundle.spawn(world)
    gameobject.add_child(status)
    gameobject.get_component(StatusManager).add(
        status.id, status.get_component(Status).component_type
    )


def get_status(
    world: World, gameobject: GameObject, status_type_type: Type[_CT]
) -> GameObject:
    return world.get_gameobject(gameobject.get_component_in_child(status_type_type)[0])


def remove_status(gameobject: GameObject, status: GameObject) -> None:
    """Removes a status from the given GameObject"""
    gameobject.remove_child(status)
    status_manager = gameobject.get_component(StatusManager)
    status_manager.remove(status.id)
    status.destroy()


def has_status(gameobject: GameObject, status_type: Type[Component]) -> bool:
    """Return True if the given gameobject has a status of the given type"""
    status_manager = gameobject.get_component(StatusManager)
    return status_type in status_manager


_KT = TypeVar("_KT")


def deep_merge(source: Dict[_KT, Any], other: Dict[_KT, Any]) -> Dict[_KT, Any]:
    """
    Merges two dictionaries (including any nested dictionaries) by overwriting
    fields in the source with the fields present in the other

    Parameters
    ----------
    source: Dict[_KT, Any]
        Dictionary with initial field values

    other: Dict[_KT, Any]
        Dictionary with fields to override in the source dict

    Returns
    -------
    Dict[_KT, Any]
        New dictionary with fields in source overwritten
        with values from the other
    """
    merged_dict = {**source}

    for key, value in other.items():
        if isinstance(value, dict):
            # get node or create one
            node = merged_dict.get(key, {})
            merged_dict[key] = deep_merge(node, value)  # type: ignore
        else:
            merged_dict[key] = value

    return merged_dict
