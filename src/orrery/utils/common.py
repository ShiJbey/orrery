import json
import random
from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar

import orrery.events
from orrery.components.business import (
    Business,
    ClosedForBusiness,
    Occupation,
    OpenForBusiness,
    ServiceLibrary,
    Services,
    WorkHistory,
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
    Activities,
    ActivityInstance,
    ActivityLibrary,
    ActivityToVirtueMap,
    LikedActivities,
)
from orrery.core.ecs import Component, ComponentBundle, GameObject, World
from orrery.core.event import EventHandler
from orrery.core.relationship import RelationshipManager, RelationshipTag
from orrery.core.settlement import Settlement, create_grid_settlement
from orrery.core.time import SimDateTime
from orrery.core.tracery import Tracery
from orrery.core.virtues import Virtues
from orrery.utils.relationships import get_relationship


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
        overrides[GameCharacter]["life_stage"] = life_stage.name

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
    settlement_comp.land_map.reserve_lot(lot, business.uid)

    # Set the position of the building
    position = settlement_comp.land_map.get_lot_position(lot)
    business.get_component(Position2D).x = position[0]
    business.get_component(Position2D).y = position[1]

    # Give the business a building
    business.add_component(
        Building(building_type="commercial", lot=lot, settlement=settlement.uid)
    )
    business.add_component(OpenForBusiness())
    business.add_component(Active())

    return business


def add_residence(
    residence: GameObject, settlement: GameObject, lot: int
) -> GameObject:
    settlement_comp = settlement.get_component(Settlement)

    # Reserve the space
    settlement_comp.land_map.reserve_lot(lot, residence.uid)

    # Set the position of the building
    position = settlement_comp.land_map.get_lot_position(lot)
    residence.get_component(Position2D).x = position[0]
    residence.get_component(Position2D).y = position[1]

    # Give the business a building
    residence.add_component(
        Building(building_type="residential", lot=lot, settlement=settlement.uid)
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

        if former_residence.is_owner(character.uid):
            former_residence.remove_owner(character.uid)

        former_residence.remove_resident(character.uid)
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
    new_residence.get_component(Residence).add_resident(character.uid)
    new_settlement = world.get_gameobject(
        new_residence.get_component(Residence).settlement
    )

    if is_owner:
        new_residence.get_component(Residence).add_owner(character.uid)

    character.add_component(
        Resident(residence=new_residence.uid, settlement=new_settlement.uid)
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

    world.get_resource(EventHandler).record_event(
        orrery.events.DepartEvent(
            date=world.get_resource(SimDateTime),
            characters=departing_characters,
            reason=reason,
        )
    )


def set_business_name(business: GameObject, name: str) -> None:
    """Sets the name of a business"""
    business.name = name
    business.get_component(Business).name = name


def set_character_name(character: GameObject, first_name: str, last_name: str) -> None:
    """Sets the name of a business"""
    game_character = character.get_component(GameCharacter)
    game_character.first_name = first_name
    game_character.last_name = last_name
    character.name = game_character.full_name


#######################################
# Business Management
#######################################


def add_coworkers(character: GameObject, business: GameObject) -> None:
    """Add coworker tags to current coworkers in relationship network"""
    for employee_id in business.get_component(Business).get_employees():
        if employee_id == character.uid:
            continue

        coworker = character.world.get_gameobject(employee_id)

        get_relationship(character, coworker, True).add_tags(RelationshipTag.Coworker)
        get_relationship(character, coworker).interaction_score += 1

        get_relationship(coworker, character, True).add_tags(RelationshipTag.Coworker)
        get_relationship(coworker, character).interaction_score += 1


def remove_coworkers(character: GameObject, business: GameObject) -> None:
    """Remove coworker tags from current coworkers in relationship network"""
    for employee_id in business.get_component(Business).get_employees():
        if employee_id == character.uid:
            continue

        coworker = character.world.get_gameobject(employee_id)

        get_relationship(character, coworker, True).remove_tags(
            RelationshipTag.Coworker
        )
        get_relationship(character, coworker).interaction_score += -1

        get_relationship(coworker, character, True).remove_tags(
            RelationshipTag.Coworker
        )
        get_relationship(coworker, character).interaction_score += -1


def shutdown_business(business: GameObject) -> None:
    """Close a business and remove all employees and the owner"""
    world = business.world
    date = world.get_resource(SimDateTime)

    event = orrery.events.BusinessClosedEvent(date, business)

    business.remove_component(OpenForBusiness)
    business.add_component(ClosedForBusiness())

    world.get_resource(EventHandler).record_event(event)

    business_comp = business.get_component(Business)

    for employee in business_comp.get_employees():
        end_job(world, world.get_gameobject(employee), reason=event.name)

    if business_comp.owner_type is not None and business_comp.owner is not None:
        end_job(world, world.get_gameobject(business_comp.owner), reason=event.name)

    location = business.get_component(Location)

    for frequenter_id in location.frequented_by:
        world.get_gameobject(frequenter_id).get_component(
            FrequentedLocations
        ).locations.remove(business.uid)

    business.remove_component(Active)
    business.remove_component(Location)
    demolish_building(world, business)


def start_job(
    business: Business,
    character: GameObject,
    occupation: Occupation,
    is_owner: bool = False,
) -> None:
    if is_owner:
        business.owner = character.uid

    business.add_employee(character.uid, occupation.occupation_type)
    character.add_component(occupation)

    add_coworkers(character, business.gameobject)


def end_job(
    world: World,
    character: GameObject,
    reason: str,
) -> None:
    occupation = character.get_component(Occupation)
    business = world.get_gameobject(occupation.business)
    business_comp = business.get_component(Business)

    # Update the former employees RelationshipManager
    remove_coworkers(character, business)

    if business_comp.owner_type is not None and business_comp.owner == character.uid:
        business_comp.set_owner(None)

    business_comp.remove_employee(character.uid)

    character.remove_component(Occupation)

    # Update the former employee's work history
    if not character.has_component(WorkHistory):
        character.add_component(WorkHistory())

    character.get_component(WorkHistory).add_entry(
        occupation_type=occupation.occupation_type,
        business=business.uid,
        years_held=occupation.years_held,
    )

    # Emit the event
    world.get_resource(EventHandler).record_event(
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
    service_library = world.get_resource(ServiceLibrary)
    for gid, services_component in world.get_component(Services):
        if all(
            [services_component.has_service(service_library.get(s)) for s in services]
        ):
            matches.append(gid)
    return matches


#######################################
# Activities and Location Frequenting
#######################################


def set_liked_activities(
    world: World, character: GameObject, max_activities: int = 3
) -> None:
    """
    Determine the activities a character likes to do

    Parameters
    ----------
    world: World
        The World instance of the simulation
    character: GameObject
        The character to set liked activities for
    max_activities: int
        The maximum number of activities to select
    """

    scores: List[Tuple[float, ActivityInstance]] = []

    activities_to_virtues = world.get_resource(ActivityToVirtueMap)

    virtue_vect = character.get_component(Virtues)

    for activity in world.get_resource(ActivityLibrary):
        activity_virtues = activities_to_virtues.mappings.get(activity, Virtues())
        score = virtue_vect.compatibility(activity_virtues)
        scores.append((score, activity))

    liked_activities = LikedActivities(
        set(
            [
                activity_score[1]
                for activity_score in sorted(scores, key=lambda s: s[0], reverse=True)
            ][:max_activities]
        )
    )

    character.add_component(liked_activities)


def find_places_with_activities(
    world: World, settlement: GameObject, *activities: str
) -> List[int]:
    """
    Find businesses within the given settlement with all the given activities

    Parameters
    ----------
    world: World
        The World instance of the simulation
    settlement: GameObject
        The settlement to search within
    *activities: str
        Activities to search for

    Returns
    -------
    List[int]
         Returns the identifiers of locations
    """
    activity_library = world.get_resource(ActivityLibrary)

    matches: List[int] = []

    settlement_comp = settlement.get_component(Settlement)

    activity_instances = [activity_library.get(a, create_new=False) for a in activities]

    for location_id in settlement_comp.places_with_activities:
        location_activities = world.get_gameobject(location_id).get_component(
            Activities
        )
        if all([a in location_activities for a in activity_instances]):
            matches.append(location_id)

    return matches


def find_places_with_any_activities(
    world: World, settlement: GameObject, *activities: str
) -> List[int]:
    """
    Find businesses within the given settlement with any of the given activities

    Parameters
    ----------
    world: World
        The World instance of the simulation
    settlement: GameObject
        The settlement to search within
    *activities: str
        Activities to search for

    Returns
    -------
    List[int]
         Returns the identifiers of locations
    """
    activity_library = world.get_resource(ActivityLibrary)

    activity_instances = [activity_library.get(a, create_new=False) for a in activities]

    def score_location(loc: Activities) -> int:
        location_score: int = 0
        for activity in activity_instances:
            if activity in loc:
                location_score += 1
        return location_score

    matches: List[Tuple[int, int]] = []

    settlement_comp = settlement.get_component(Settlement)

    for location_id in settlement_comp.places_with_activities:
        score = score_location(
            world.get_gameobject(location_id).get_component(Activities)
        )
        if score > 0:
            matches.append((score, location_id))

    return [match[1] for match in sorted(matches, key=lambda m: m[0], reverse=True)]


def set_frequented_locations(
    world: World, character: GameObject, settlement: GameObject, max_locations: int = 3
) -> None:
    """
    Set what locations a character frequents based on the locations within
    a given settlement

    Parameters
    ----------
    world: World
        The world instance of the simulation
    character: GameObject
        The character oto set frequented locations for
    settlement: GameObject
        The settlement to sample frequented locations from
    max_locations: int
        The max number of locations to sample
    """
    clear_frequented_locations(world, character)

    liked_activities = [
        a.name for a in character.get_component(LikedActivities).activities
    ]

    locations = find_places_with_any_activities(
        world, settlement, *list(liked_activities)
    )

    selected_locations = locations[:max_locations]

    character.add_component(FrequentedLocations(set(selected_locations)))

    for loc_id in selected_locations:
        world.get_gameobject(loc_id).get_component(Location).frequented_by.add(
            character.uid
        )


def clear_frequented_locations(world: World, character: GameObject) -> None:
    """
    Un-mark any locations as frequented by the given character

    Parameters
    ----------
    world: World
        The World instance of the simulation
    character: GameObject
        The GameObject to remove as a frequenter
    """
    if frequented_locations := character.try_component(FrequentedLocations):
        for location_id in frequented_locations.locations:
            location = world.get_gameobject(location_id).get_component(Location)
            location.frequented_by.remove(character.uid)
        frequented_locations.locations.clear()
        character.remove_component(FrequentedLocations)


def add_character_to_settlement(
    world: World, character: GameObject, settlement: GameObject
) -> None:
    """
    Adds a character to a settlement and sets required fields for decision-making

    Parameters
    ----------
    world: World
        The World instance of ths simulation
    character: GameObject
        The character to add
    settlement: GameObject
        The settlement to add the character to
    """

    set_liked_activities(world, character)
    set_frequented_locations(world, character, settlement)

    character.add_component(Active())

    world.get_resource(EventHandler).record_event(
        orrery.events.JoinSettlementEvent(
            world.get_resource(SimDateTime), settlement, character
        )
    )


#######################################
# General Utility Functions
#######################################

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


def pprint_gameobject(gameobject: GameObject) -> None:
    """Pretty prints a GameObject"""
    print(
        json.dumps(
            gameobject.to_dict(),
            sort_keys=True,
            indent=2,
        )
    )
