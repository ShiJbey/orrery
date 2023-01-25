import json
import random
from typing import Any, Dict, Iterable, List, Optional, Tuple, TypeVar

import orrery.events
from orrery.components.activity import ActivityInstance, LikedActivities
from orrery.components.business import (
    BossOf,
    Business,
    BusinessOwner,
    ClosedForBusiness,
    CoworkerOf,
    EmployeeOf,
    Occupation,
    OpenForBusiness,
    Services,
    Unemployed,
    WorkHistory,
)
from orrery.components.character import (
    GameCharacter,
    Gender,
    LifeStage,
    Married,
    ParentOf,
)
from orrery.components.residence import Residence, Resident, Vacant
from orrery.components.settlement import GridSettlementMap, Settlement
from orrery.components.shared import (
    Active,
    Building,
    CurrentSettlement,
    FrequentedLocations,
    Location,
    Position2D,
)
from orrery.components.virtues import Virtues
from orrery.content_management import (
    ActivityLibrary,
    ActivityToVirtueMap,
    CharacterLibrary,
    ServiceLibrary,
)
from orrery.core.ecs import GameObject, World
from orrery.core.event import EventHandler
from orrery.core.time import SimDateTime
from orrery.core.tracery import Tracery
from orrery.prefabs import BusinessPrefab, CharacterPrefab, ResidencePrefab
from orrery.utils.relationships import (
    add_relationship_status,
    get_relationship,
    has_relationship_status,
    remove_relationship_status,
)
from orrery.utils.statuses import add_status, has_status, remove_status


def create_settlement(
    world: World,
    settlement_name: str = "#settlement_name#",
    settlement_size: Tuple[int, int] = (5, 5),
) -> GameObject:
    """Create a new grid-based Settlement GameObject and add it to the world

    Parameters
    ----------
    world: World
        The world instance to add the settlement to
    settlement_name: str
        A tracery grammar that expands to the name of the settlement
        (defaults to "#settlement_name#")
    settlement_size: Tuple[int, int], optional
        The X, Y dimensions of the map of the town (defaults to (5, 5))

    Returns
    -------
    GameObject
        The newly created Settlement GameObject
    """
    generated_name = world.get_resource(Tracery).generate(settlement_name)

    settlement = world.spawn_gameobject(
        [Settlement(generated_name, GridSettlementMap(settlement_size))]
    )

    world.get_resource(EventHandler).emit(
        orrery.events.NewSettlementEvent(
            date=world.get_resource(SimDateTime), settlement=settlement
        )
    )

    return settlement


def add_location_to_settlement(
    location: GameObject,
    settlement: GameObject,
) -> None:
    """Add a location to a settlement

    Parameters
    ----------
    location: GameObject
        The location to add
    settlement: GameObject
        The settlement to add the location to
    """
    settlement.get_component(Settlement).locations.add(location.uid)


def remove_location_from_settlement(
    location: GameObject,
    settlement: GameObject,
) -> None:
    """Remove a location from a settlement

    Parameters
    ----------
    location: GameObject
        The location to remove
    settlement: GameObject
        The settlement to remove the location from
    """
    settlement.get_component(Settlement).locations.remove(location.uid)


def create_character(
    world: World,
    prefab: CharacterPrefab,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    age: Optional[int] = None,
    life_stage: Optional[LifeStage] = None,
    gender: Optional[Gender] = None,
) -> GameObject:
    """Create a new GameCharacter GameObject and add it to the world

    Parameters
    ----------
    world: World
        The world instance to add the character to
    prefab: CharacterPrefab
        A bundle used to construct the character
    first_name: str, optional
        first name override (defaults to None)
    last_name: str, optional
        last name override (defaults to None)
    age: int, optional
        age override (defaults to None)
    life_stage: LifeStage, optional
        life stage override (defaults to None)
    gender: str, optional
        gender override (defaults to None)

    Returns
    -------
    GameObject
        The newly constructed character
    """
    character = prefab.spawn(world)

    if first_name:
        character.get_component(GameCharacter).first_name = first_name

    if last_name:
        character.get_component(GameCharacter).last_name = last_name

    if age:
        character.get_component(GameCharacter).overwrite_age(age)

    if life_stage:
        character.get_component(GameCharacter).overwrite_life_stage(life_stage)

    if gender:
        character.get_component(GameCharacter).gender = gender

    world.get_resource(EventHandler).emit(
        orrery.events.NewCharacterEvent(
            date=world.get_resource(SimDateTime), character=character
        )
    )

    return character


def add_character_to_settlement(character: GameObject, settlement: GameObject) -> None:
    """Adds a character to a settlement and sets required fields for decision-making

    Parameters
    ----------
    character: GameObject
        The character to add
    settlement: GameObject
        The settlement to add the character to
    """
    current_date = character.world.get_resource(SimDateTime).to_iso_str()
    set_liked_activities(character.world, character)
    set_frequented_locations(character.world, character, settlement)

    add_status(character, Active(current_date))

    character.add_component(CurrentSettlement(settlement.uid))

    character.world.get_resource(EventHandler).emit(
        orrery.events.JoinSettlementEvent(
            character.world.get_resource(SimDateTime), settlement, character
        )
    )


def remove_character_from_settlement(
    character: GameObject, settlement: GameObject
) -> None:
    """Remove a character from a settlement and set required fields for decision-making

    Parameters
    ----------
    character: GameObject
        The character to add
    settlement: GameObject
        The settlement to add the character to
    """

    set_liked_activities(character.world, character)
    set_frequented_locations(character.world, character, settlement)

    remove_status(character, Active)

    character.world.get_resource(EventHandler).emit(
        orrery.events.LeaveSettlementEvent(
            character.world.get_resource(SimDateTime), settlement, character
        )
    )


def create_residence(
    world: World,
    prefab: ResidencePrefab,
) -> GameObject:
    residence = prefab.spawn(world)

    world.get_resource(EventHandler).emit(
        orrery.events.NewResidenceEvent(
            date=world.get_resource(SimDateTime), residence=residence
        )
    )

    return residence


def add_residence(
    residence: GameObject, settlement: GameObject, lot: int
) -> GameObject:
    current_date = residence.world.get_resource(SimDateTime).to_iso_str()
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

    add_status(residence, Vacant(current_date))
    add_status(residence, Active(current_date))

    return residence


def generate_child_prefab(
    world: World, parent_a: GameObject, parent_b: GameObject
) -> CharacterPrefab:
    rng = world.get_resource(random.Random)
    library = world.get_resource(CharacterLibrary)

    eligible_child_configs = [
        *parent_a.get_component(GameCharacter).config.spawning.child_archetypes,
        *parent_b.get_component(GameCharacter).config.spawning.child_archetypes,
    ]

    potential_child_bundles = library.get_matching_prefabs(*eligible_child_configs)

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

        bundle = library.get(config_to_inherit.name)

        return bundle


def set_residence(
    world: World,
    character: GameObject,
    new_residence: Optional[GameObject],
    is_owner: bool = False,
) -> None:
    """
    Moves a character into a new permanent residence
    """
    current_date = world.get_resource(SimDateTime).to_iso_str()

    if resident := character.try_component(Resident):
        # This character is currently a resident at another location
        former_residence = world.get_gameobject(resident.residence)
        former_residence_comp = former_residence.get_component(Residence)

        if former_residence_comp.is_owner(character.uid):
            former_residence_comp.remove_owner(character.uid)

        former_residence_comp.remove_resident(character.uid)
        remove_status(character, Resident)

        former_settlement = world.get_gameobject(
            character.get_component(CurrentSettlement).settlement
        ).get_component(Settlement)

        former_settlement.population -= 1

        if len(former_residence_comp.residents) <= 0:
            add_status(former_residence, Vacant(current_date))

        character.remove_component(CurrentSettlement)

    if new_residence is None:
        return

    # Move into new residence
    new_residence.get_component(Residence).add_resident(character.uid)

    new_settlement = world.get_gameobject(
        new_residence.get_component(CurrentSettlement).settlement
    )

    if is_owner:
        new_residence.get_component(Residence).add_owner(character.uid)

    add_status(
        character,
        Resident(created=current_date, residence=new_residence.uid),
    )

    character.add_component(CurrentSettlement(new_settlement.uid))

    if new_residence.has_component(Vacant):
        remove_status(new_residence, Vacant)

    new_settlement.get_component(Settlement).population += 1


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

        if has_relationship_status(character, resident, Married):
            set_residence(world, resident, None)
            departing_characters.append(resident)

        elif has_relationship_status(character, resident, ParentOf):
            set_residence(world, resident, None)
            departing_characters.append(resident)

    world.get_resource(EventHandler).emit(
        orrery.events.DepartEvent(
            date=world.get_resource(SimDateTime),
            characters=departing_characters,
            reason=reason,
        )
    )


def set_character_name(character: GameObject, first_name: str, last_name: str) -> None:
    """Sets the name of a business"""
    game_character = character.get_component(GameCharacter)
    game_character.first_name = first_name
    game_character.last_name = last_name
    character.name = game_character.full_name


#######################################
# Business Management
#######################################


def set_business_name(business: GameObject, name: str) -> None:
    """Sets the name of a business"""
    business.name = name
    business.get_component(Business).name = name


def create_business(
    world: World,
    prefab: BusinessPrefab,
    name: Optional[str] = None,
) -> GameObject:
    business = prefab.spawn(world)

    if name:
        business.get_component(Business).name = name

    world.get_resource(EventHandler).emit(
        orrery.events.NewBusinessEvent(
            date=world.get_resource(SimDateTime), business=business
        )
    )

    return business


def startup_business(
    business: GameObject,
    settlement: GameObject,
    lot_id: Optional[int] = None,
) -> None:
    """Add a business gameobject to a settlement

    Parameters
    ----------
    business: GameObject
        The business to add
    settlement: GameObject
        The settlement to add the business to
    lot_id: int, optional
        The lot to place the business on (defaults to None)
    """
    current_date = settlement.world.get_resource(SimDateTime).to_iso_str()

    settlement_comp = settlement.get_component(Settlement)

    if lot_id is None:
        # If a lot is not supplied, get the first available lot
        # If none is available this will throw an IndexError which is
        # fine since we don't want this to succeed if there is nowhere
        # to build
        lot_id = settlement_comp.land_map.get_vacant_lots()[0]

    # Increase the count of this business type in the settlement
    settlement_comp.business_counts[business.get_component(Business).config.name] += 1
    settlement_comp.businesses.add(business.uid)

    # Reserve the space
    settlement_comp.land_map.reserve_lot(lot_id, business.uid)

    # Set the position of the building
    lot_position = settlement_comp.land_map.get_lot_position(lot_id)
    business.add_component(Position2D(lot_position[0], lot_position[1]))

    # Give the business a building
    business.add_component(
        Building(building_type="commercial", lot=lot_id, settlement=settlement.uid)
    )

    # Mark the business as an active GameObject
    add_status(business, Active(current_date))
    add_status(business, OpenForBusiness(current_date))

    # Add the business as a location within the town if it has a location component
    if business.has_component(Location):
        add_location_to_settlement(business, settlement)


def shutdown_business(business: GameObject) -> None:
    """Close a business and remove all employees and the owner

    This shuts down the business, but it does not remove it from the
    town map. That has to be done with the 'remove_business' function

    Parameters
    ----------
    business: GameObject
        Business to shut down in the town
    """
    world = business.world
    date = world.get_resource(SimDateTime)
    business_comp = business.get_component(Business)
    building = business.get_component(Building)
    settlement_obj = business.world.get_gameobject(building.settlement)
    settlement = settlement_obj.get_component(Settlement)

    event = orrery.events.BusinessClosedEvent(date, business)

    # Update the business as no longer active
    remove_status(business, OpenForBusiness)
    add_status(business, ClosedForBusiness(date.to_iso_str()))

    # Remove all the employees
    for employee in business_comp.get_employees():
        end_job(world.get_gameobject(employee), reason=event.name)

    # Remove the owner if applicable
    if business_comp.owner is not None:
        end_job(world.get_gameobject(business_comp.owner), reason=event.name)

    location = business.get_component(Location)

    # Remove this location from the places that characters frequent
    for frequenter_id in location.frequented_by:
        world.get_gameobject(frequenter_id).get_component(
            FrequentedLocations
        ).locations.remove(business.uid)

    # Decrement the number of this type
    settlement.business_counts[business_comp.config.name] -= 1
    settlement.businesses.remove(business.uid)

    if business.has_component(Location):
        remove_location_from_settlement(business, settlement_obj)

    # Demolish the building
    settlement.land_map.free_lot(building.lot)
    business.remove_component(Building)
    business.remove_component(Position2D)

    # Un-mark the business as active so it doesn't appear in queries
    business.remove_component(Location)
    remove_status(business, Active)

    world.get_resource(EventHandler).emit(event)


def end_job(
    character: GameObject,
    reason: str = "",
) -> None:
    """End a characters current occupation

    Parameters
    ----------
    character: GameObject
        The characters whose job to terminate
    reason: str, optional
        The reason for them leaving their job (defaults to "")
    """
    world = character.world
    current_date = world.get_resource(SimDateTime).to_iso_str()
    occupation = character.get_component(Occupation)
    business = world.get_gameobject(occupation.business)
    business_comp = business.get_component(Business)

    if character.has_component(BusinessOwner):
        remove_status(character, BusinessOwner)
        business_comp.set_owner(None)

        # Update relationships boss/employee relationships
        for employee_id in business.get_component(Business).get_employees():
            employee = world.get_gameobject(employee_id)

            remove_relationship_status(character, employee, BossOf)
            remove_relationship_status(employee, character, EmployeeOf)

            get_relationship(character, employee).interaction_score += -1
            get_relationship(employee, character).interaction_score += -1

    else:
        business_comp.remove_employee(character.uid)

        # Update boss/employee relationships if needed
        if business_comp.owner is not None:
            owner = world.get_gameobject(business_comp.owner)
            remove_relationship_status(owner, character, BossOf)
            remove_relationship_status(character, owner, EmployeeOf)

            get_relationship(character, owner).interaction_score += -1
            get_relationship(owner, character).interaction_score += -1

        # Update coworker relationships
        for employee_id in business.get_component(Business).get_employees():
            employee = world.get_gameobject(employee_id)

            remove_relationship_status(character, employee, CoworkerOf)
            remove_relationship_status(employee, character, CoworkerOf)

            get_relationship(character, employee).interaction_score += -1
            get_relationship(employee, character).interaction_score += -1

    character.remove_component(Occupation)

    add_status(character, Unemployed(current_date))

    # Update the former employee's work history
    if not character.has_component(WorkHistory):
        character.add_component(WorkHistory())

    character.get_component(WorkHistory).add_entry(
        occupation_type=occupation.occupation_type,
        business=business.uid,
        years_held=occupation.years_held,
        reason_for_leaving=reason,
    )

    # Emit the event
    world.get_resource(EventHandler).emit(
        orrery.events.EndJobEvent(
            date=world.get_resource(SimDateTime),
            character=character,
            business=business,
            occupation=occupation.occupation_type,
            reason=reason,
        )
    )


def start_job(
    character: GameObject,
    business: GameObject,
    occupation_name: str,
    is_owner: bool = False,
) -> None:
    """Start the given character's job at the business

    Parameters
    ----------
    character: GameObject
        The character starting the job
    business: GameObject
        The business they will start working at
    occupation_name: str
        The job title for their new occupation
    is_owner: bool, optional
        Is this character going to be the owner of the
        business (defaults to False)

    Raises
    ------
    RuntimeError
        If attempting to set the character as the business owner
        and the business owner is not None
    """
    world = character.world
    current_date = world.get_resource(SimDateTime).to_iso_str()
    business_comp = business.get_component(Business)
    occupation = Occupation(occupation_name, business.uid)

    if character.has_component(Occupation):
        # Character must quit the old job before taking a new one
        raise RuntimeError("Cannot start a new job with existing Occupation component.")

    character.add_component(occupation)

    if has_status(character, Unemployed):
        remove_status(character, Unemployed)

    if is_owner:
        if business_comp.owner is not None:
            # The old owner needs to be removed before setting a new one
            raise RuntimeError("Owner is already set. Please end job first.")

        if business_comp.config.owner_type is None:
            # You cannot set an owner of a business that should not have one
            # meaning that it is municipal
            raise RuntimeError(
                "Cannot set owner for business that has owner_type None."
            )

        business_comp.set_owner(character.uid)
        add_status(
            character, BusinessOwner(business=business.uid, created=current_date)
        )

        for employee_id in business.get_component(Business).get_employees():
            employee = world.get_gameobject(employee_id)
            add_relationship_status(character, employee, BossOf(current_date))
            add_relationship_status(employee, character, EmployeeOf(current_date))
            get_relationship(character, employee).interaction_score += 1
            get_relationship(employee, character).interaction_score += 1

    else:
        # Update boss/employee relationships if needed
        if business_comp.owner is not None:
            owner = world.get_gameobject(business_comp.owner)
            add_relationship_status(owner, character, BossOf(current_date))
            add_relationship_status(character, owner, EmployeeOf(current_date))

            get_relationship(character, owner).interaction_score += 1
            get_relationship(owner, character).interaction_score += 1

        # Update employee/employee relationships
        for employee_id in business.get_component(Business).get_employees():
            employee = world.get_gameobject(employee_id)
            add_relationship_status(character, employee, CoworkerOf(current_date))
            add_relationship_status(employee, character, CoworkerOf(current_date))
            get_relationship(character, employee).interaction_score += 1
            get_relationship(employee, character).interaction_score += 1

        business_comp.add_employee(character.uid, occupation.occupation_type)

    character.world.get_resource(EventHandler).emit(
        orrery.events.StartJobEvent(
            character.world.get_resource(SimDateTime),
            business=business,
            character=character,
            occupation=occupation.occupation_type,
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

    for location_id in settlement_comp.locations:
        location_activities = (
            world.get_gameobject(location_id).get_component(Location).activities
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

    def score_location(act_list: Iterable[ActivityInstance]) -> int:
        location_score: int = 0
        for activity in activity_instances:
            if activity in act_list:
                location_score += 1
        return location_score

    matches: List[Tuple[int, int]] = []

    settlement_comp = settlement.get_component(Settlement)

    for location_id in settlement_comp.locations:
        score = score_location(
            world.get_gameobject(location_id).get_component(Location).activities
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
    clear_frequented_locations(character)

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


def clear_frequented_locations(character: GameObject) -> None:
    """
    Un-mark any locations as frequented by the given character

    Parameters
    ----------
    character: GameObject
        The GameObject to remove as a frequenter
    """
    world = character.world
    if frequented_locations := character.try_component(FrequentedLocations):
        for location_id in frequented_locations.locations:
            location = world.get_gameobject(location_id).get_component(Location)
            location.frequented_by.remove(character.uid)
        frequented_locations.locations.clear()
        character.remove_component(FrequentedLocations)


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
