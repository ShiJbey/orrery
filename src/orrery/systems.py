import random
from abc import ABC, abstractmethod
from collections import Counter
from typing import Any, List, Optional, Type

from ordered_set import OrderedSet

import orrery.events
from orrery.components.business import (
    Business,
    BusinessLibrary,
    Occupation,
    OccupationType,
    OccupationTypeLibrary,
    OpenForBusiness,
)
from orrery.components.character import (
    CanAge,
    CharacterLibrary,
    Departed,
    GameCharacter,
    LifeStage,
)
from orrery.components.residence import Residence, ResidenceLibrary, Resident, Vacant
from orrery.components.shared import (
    Active,
    Building,
    CurrentSettlement,
    FrequentedLocations,
    Location,
)
from orrery.components.statuses import (
    ChildOf,
    Dating,
    InTheWorkforce,
    Married,
    ParentOf,
    Pregnant,
    SiblingOf,
    Unemployed,
)
from orrery.core.config import CharacterConfig, OrreryConfig
from orrery.core.ecs import ComponentBundle, GameObject, ISystem
from orrery.core.ecs.query import QueryBuilder
from orrery.core.event import Event, EventHandler, EventRole
from orrery.core.life_event import LifeEventLibrary
from orrery.core.relationship import Relationship, lerp
from orrery.core.settlement import Settlement
from orrery.core.time import DAYS_PER_YEAR, SimDateTime, TimeDelta
from orrery.utils.common import (
    add_character_to_settlement,
    add_residence,
    check_share_residence,
    clear_frequented_locations,
    create_business,
    create_character,
    create_residence,
    generate_child_bundle,
    set_residence,
    start_job,
    startup_business,
)
from orrery.utils.relationships import (
    add_relationship,
    add_relationship_status,
    get_relationship,
    get_relationships_with_statuses,
    has_relationship,
)
from orrery.utils.statuses import add_status, remove_status


class System(ISystem):
    """
    System is a more fully-featured System abstraction that
    handles common calculations like calculating the elapsed
    time between calls.
    """

    __slots__ = "_interval", "_last_run", "_elapsed_time", "_next_run"

    def __init__(
        self,
        interval: Optional[TimeDelta] = None,
    ) -> None:
        super(ISystem, self).__init__()
        self._last_run: Optional[SimDateTime] = None
        self._interval: TimeDelta = interval if interval else TimeDelta()
        self._next_run: SimDateTime = SimDateTime() + self._interval
        self._elapsed_time: TimeDelta = TimeDelta()

    @property
    def elapsed_time(self) -> TimeDelta:
        """Returns the amount of simulation time since the last update"""
        return self._elapsed_time

    def process(self, *args: Any, **kwargs: Any) -> None:
        """Handles internal bookkeeping before running the system"""
        date = self.world.get_resource(SimDateTime)

        if date >= self._next_run:
            if self._last_run is None:
                self._elapsed_time = TimeDelta()
            else:
                self._elapsed_time = date - self._last_run
            self._last_run = date.copy()
            self._next_run = date + self._interval
            self.run(*args, **kwargs)

    @abstractmethod
    def run(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError


class TimeSystem(ISystem):
    """Advances the current date of the simulation"""

    def process(self, *args: Any, **kwargs: Any) -> None:
        # Get time increment from the simulation configuration
        # this may be slow, but it is the cleanest configuration thus far
        increment = self.world.get_resource(OrreryConfig).time_increment
        current_date = self.world.get_resource(SimDateTime)
        current_date.increment(months=increment)


class ISystemGroup(ISystem, ABC):
    """Abstract base class for all system group classes"""

    @abstractmethod
    def add_subsystem(self, sub_system: ISystem) -> None:
        """Add a sub-system to the system group"""
        raise NotImplementedError

    @abstractmethod
    def remove_subsystem(self, system_type: Type[ISystem]) -> None:
        """Remove a sub-system from the group"""
        raise NotImplementedError


class RootSystemGroup(ISystemGroup):
    """The default system group to which systems are added"""

    name: str = "root"
    active: bool = True

    __slots__ = "sub_systems"

    def __init__(self) -> None:
        self.sub_systems: OrderedSet[ISystem] = OrderedSet([])

    @classmethod
    def get_name(cls) -> str:
        """Return the name of the system"""
        return cls.name

    def system_should_run(self) -> bool:
        """Check if this system should run this simulation step

        Returns
        -------
        bool
            Returns True if the system should run
        """

        return self.active

    def add_subsystem(self, system: ISystem) -> None:
        """Add a sub-system to the system group"""
        self.sub_systems.add(system)

    def remove_subsystem(self, system: ISystem) -> None:
        """Remove a sub-system from the group"""
        self.sub_systems.remove(system)

    def process(self, *args, **kwargs) -> None:
        for s in self.sub_systems:
            s.process(*args, **kwargs)


class LifeEventSystem(System):
    """Fires LifeEvents adding some spice to the simulation data"""

    def run(self, *args: Any, **kwarg: Any) -> None:
        """Simulate LifeEvents for characters"""
        rng = self.world.get_resource(random.Random)
        life_events = self.world.get_resource(LifeEventLibrary)
        all_events = life_events.get_all()

        if all_events:
            for _, settlement in self.world.get_component(Settlement):
                for life_event in rng.choices(all_events, k=10):
                    life_event.try_execute_event(self.world)


class MeetNewPeopleSystem(ISystem):
    """Characters meet new people based on places they frequent"""

    def process(self, *args: Any, **kwargs: Any):
        for gid, _ in self.world.get_components(GameCharacter, Active):
            character = self.world.get_gameobject(gid)

            frequented_locations = character.get_component(
                FrequentedLocations
            ).locations

            candidates: List[int] = []

            for loc_id in frequented_locations:
                for other_id in (
                    self.world.get_gameobject(loc_id)
                    .get_component(Location)
                    .frequented_by
                ):
                    other = self.world.get_gameobject(other_id)
                    if other_id != character.uid and not has_relationship(
                        character, other
                    ):
                        candidates.append(other_id)

            if candidates:
                candidate_weights = Counter(candidates)

                # Select one randomly
                options: List[int]
                weights: List[int]
                options, weights = zip(*candidate_weights.items())

                rng = self.world.get_resource(random.Random)

                acquaintance_id = rng.choices(options, weights=weights, k=1)[0]

                acquaintance = self.world.get_gameobject(acquaintance_id)

                if not has_relationship(character, acquaintance):

                    add_relationship(character, acquaintance)
                    add_relationship(acquaintance, character)

                    # Calculate interaction scores
                    index = options.index(acquaintance_id)
                    get_relationship(
                        character, acquaintance
                    ).interaction_score += weights[index]
                    get_relationship(
                        acquaintance, character
                    ).interaction_score += weights[index]


class FindEmployeesSystem(ISystem):
    """Finds employees to work open positions at businesses"""

    def process(self, *args: Any, **kwargs: Any) -> None:
        occupation_types = self.world.get_resource(OccupationTypeLibrary)
        rng = self.world.get_resource(random.Random)

        business: Business
        for guid, (business, _) in self.world.get_components(Business, OpenForBusiness):
            open_positions = business.get_open_positions()

            for occupation_name in open_positions:
                occupation_type = occupation_types.get(occupation_name)

                candidate_query = QueryBuilder(occupation_name).with_(
                    (InTheWorkforce, Active, Unemployed)
                )

                if occupation_type.precondition:
                    candidate_query.filter_(occupation_type.precondition)

                candidate_list = candidate_query.build().execute(self.world)

                if not candidate_list:
                    continue

                candidate = self.world.get_gameobject(rng.choice(candidate_list)[0])

                start_job(candidate, self.world.get_gameobject(guid), occupation_name)


class BuildHousingSystem(ISystem):
    """
    Builds housing on unoccupied spaces on the land grid
    """

    def process(self, *args: Any, **kwargs: Any) -> None:
        """Build a new residence when there is space"""
        rng = self.world.get_resource(random.Random)
        residence_library = self.world.get_resource(ResidenceLibrary)

        for settlement_id, settlement in self.world.get_component(Settlement):
            vacancies = settlement.land_map.get_vacant_lots()

            # Return early if there is nowhere to build
            if len(vacancies) == 0:
                continue

            # Don't build more housing if 60% of the land is used for residential buildings
            if len(vacancies) / float(settlement.land_map.get_total_lots()) < 0.4:
                continue

            # Pick a random lot from those available
            lot = rng.choice(vacancies)

            bundle = residence_library.choose_random(rng)

            if bundle is None:
                continue

            add_residence(
                create_residence(self.world, bundle, settlement_id),
                settlement=self.world.get_gameobject(settlement_id),
                lot=lot,
            )


class BuildBusinessSystem(ISystem):
    """Build a new business building at a random free space on the land grid."""

    def find_business_owner(
        self, occupation_type: OccupationType
    ) -> Optional[GameObject]:
        """Find someone to run the new business

        Finds a character that is within the work force, active, unemployed, and
        satisfies the preconditions of the given occupation type to be the new
        business owner

        Parameters
        ----------
        occupation_type: OccupationType
            The occupation type of the potential business owner

        Returns
        -------
        Optional[GameObject]
            Returns the GameObject that will become the business owner or None if
            no character was found
        """
        rng = self.world.get_resource(random.Random)

        query_builder = QueryBuilder().with_((InTheWorkforce, Active, Unemployed))

        if occupation_type.precondition:
            query_builder.filter_(occupation_type.precondition)

        q = query_builder.build()

        candidate_list = q.execute(self.world)

        if candidate_list:
            # NOTE: It might be nice to eventually swap this out for a
            # selection strategy that scores the characters based on
            # who is most likely to take on this role
            return self.world.get_gameobject(rng.choice(candidate_list)[0])

        return None

    def process(self, *args: Any, **kwargs: Any) -> None:
        """Attempt to build one new business per settlement"""

        event_log = self.world.get_resource(EventHandler)
        business_library = self.world.get_resource(BusinessLibrary)
        occupation_types = self.world.get_resource(OccupationTypeLibrary)
        rng = self.world.get_resource(random.Random)

        # Orrery is configured to simulate a single settlement by default. However,
        # we still do a World.get_component call just incase there are multiple
        # settlements within the same simulation
        for settlement_id, settlement in self.world.get_component(Settlement):

            vacancies = settlement.land_map.get_vacant_lots()

            # Return early if there is nowhere to build
            if len(vacancies) == 0:
                return

            # Pick a random lot from those available
            lot = rng.choice(vacancies)

            # Pick random eligible business archetype
            bundle = business_library.choose_random(
                self.world, self.world.get_gameobject(settlement_id)
            )

            # Return early if none of the businesses entries' preconditions
            # are satisfied
            if bundle is None:
                return

            business_config = business_library.get(bundle.name)

            if business_config.owner_type is not None:
                owner_occupation_type = occupation_types.get(business_config.owner_type)
                owner = self.find_business_owner(owner_occupation_type)

                if owner is None:
                    continue

                business = create_business(self.world, bundle)

                startup_business(
                    business,
                    self.world.get_gameobject(settlement_id),
                    lot_id=lot,
                )

                event_log.record_event(
                    orrery.events.StartBusinessEvent(
                        self.world.get_resource(SimDateTime),
                        owner,
                        business,
                        owner_occupation_type.name,
                        business.get_component(Business).name,
                    )
                )

                start_job(owner, business, owner_occupation_type.name, is_owner=True)

            else:
                business = create_business(self.world, bundle)

                startup_business(
                    business,
                    self.world.get_gameobject(settlement_id),
                    lot_id=lot,
                )


class SpawnResidentSystem(System):
    """
    Adds new characters to the simulation

    Remarks
    -------
    Characters can spawn as single parents with kids
    """

    __slots__ = "chance_spawn"

    def __init__(
        self,
        chance_spawn: float = 0.5,
        interval: Optional[TimeDelta] = None,
    ) -> None:
        super().__init__(interval=interval)
        self.chance_spawn: float = chance_spawn

    @staticmethod
    def _try_get_spouse_bundle(
        rng: random.Random,
        character_config: CharacterConfig,
        character_library: CharacterLibrary,
    ) -> Optional[ComponentBundle]:
        if rng.random() < character_config.spawning.chance_spawn_with_spouse:
            # Create another character to be their spouse
            potential_spouse_bundles = character_library.get_matching_bundles(
                *character_config.spawning.spouse_archetypes
            )

            if potential_spouse_bundles:
                return rng.choice(potential_spouse_bundles)

        return None

    def run(self, *args: Any, **kwargs: Any) -> None:
        rng = self.world.get_resource(random.Random)
        date = self.world.get_resource(SimDateTime)
        event_logger = self.world.get_resource(EventHandler)
        character_library = self.world.get_resource(CharacterLibrary)

        residence_comp: Residence
        for guid, (residence_comp, _, _, _) in self.world.get_components(
            Residence, Building, Active, Vacant
        ):
            residence = self.world.get_gameobject(guid)

            settlement = self.world.get_gameobject(residence_comp.settlement)

            # Return early if the random-roll is not sufficient
            if rng.random() > self.chance_spawn:
                return

            bundle = character_library.choose_random(rng)

            # There are no archetypes available to spawn
            if bundle is None:
                return

            # Track all the characters generated
            generated_characters: List[GameObject] = []

            # Create a new entity using the archetype

            character = create_character(
                self.world, bundle, life_stage=LifeStage.YoungAdult
            )

            generated_characters.append(character)

            character_config = character.get_component(GameCharacter).config

            add_character_to_settlement(character, settlement)
            set_residence(self.world, character, residence, True)

            spouse: Optional[GameObject] = None

            spouse_bundle = self._try_get_spouse_bundle(
                rng, character_config, character_library
            )

            if spouse_bundle:
                spouse = create_character(
                    self.world,
                    spouse_bundle,
                    last_name=character.get_component(GameCharacter).last_name,
                    life_stage=LifeStage.Adult,
                )

                generated_characters.append(spouse)

                # Move them into the home with the first character
                add_character_to_settlement(spouse, settlement)
                set_residence(self.world, spouse, residence, True)

                # Configure relationship from character to spouse
                add_relationship(character, spouse)
                add_relationship_status(character, spouse, Married())
                add_relationship_status(character, spouse, Married())
                get_relationship(character, spouse)["Romance"] += 45
                get_relationship(character, spouse)["Friendship"] += 30

                # Configure relationship from spouse to character
                add_relationship(spouse, character)
                add_relationship_status(spouse, character, Married())
                get_relationship(spouse, character)["Romance"] += 45
                get_relationship(spouse, character)["Friendship"] += 30

            num_kids = rng.randint(0, character_config.spawning.max_children_at_spawn)
            children: List[GameObject] = []

            potential_child_bundles = character_library.get_matching_bundles(
                *character_config.spawning.child_archetypes
            )

            if potential_child_bundles:
                chosen_child_bundles = rng.sample(potential_child_bundles, num_kids)

                for child_bundle in chosen_child_bundles:
                    child = create_character(
                        self.world,
                        child_bundle,
                        last_name=character.get_component(GameCharacter).last_name,
                        life_stage=LifeStage.Child,
                    )
                    generated_characters.append(child)

                    # Move them into the home with the first character
                    add_character_to_settlement(child, settlement)
                    set_residence(self.world, child, residence)

                    children.append(child)

                    # Relationship of child to character
                    add_relationship(child, character)
                    add_relationship_status(child, character, ChildOf())
                    get_relationship(child, character)["Friendship"] += 20

                    # Relationship of character to child
                    add_relationship(character, child)
                    add_relationship_status(character, child, ParentOf())
                    get_relationship(character, child)["Friendship"] += 20

                    if spouse:
                        # Relationship of child to spouse
                        add_relationship(child, spouse)
                        add_relationship_status(child, spouse, ChildOf())
                        get_relationship(child, spouse)["Friendship"] += 20

                        # Relationship of spouse to child
                        add_relationship(spouse, child)
                        add_relationship_status(spouse, child, ParentOf())
                        get_relationship(spouse, child)["Friendship"] += 20

                    for sibling in children:
                        # Relationship of child to sibling
                        add_relationship(child, sibling)
                        add_relationship_status(child, sibling, SiblingOf())
                        get_relationship(child, sibling)["Friendship"] += 20

                        # Relationship of sibling to child
                        add_relationship(sibling, child)
                        add_relationship_status(sibling, child, SiblingOf())
                        get_relationship(sibling, child)["Friendship"] += 20

            # Record a life event
            event_logger.record_event(
                orrery.events.MoveIntoTownEvent(date, residence, *generated_characters)
            )


class BusinessUpdateSystem(System):
    def run(self, *args: Any, **kwargs: Any) -> None:
        time_increment = float(self.elapsed_time.total_days) / DAYS_PER_YEAR
        business: Business
        for _, (business, _) in self.world.get_components(Business, OpenForBusiness):
            # Increment how long the business has been open for business
            business.years_in_business += time_increment


class OccupationUpdateSystem(System):
    def run(self, *args: Any, **kwargs: Any) -> None:
        for guid, occupation in self.world.get_component(Occupation):
            # Increment the amount of time that a character has held this occupation
            occupation.set_years_held(
                occupation.years_held
                + (float(self.elapsed_time.total_days) / DAYS_PER_YEAR)
            )


class CharacterAgingSystem(System):
    """
    Updates the ages of characters, adds/removes life
    stage components (Adult, Child, Elder, ...), and
    handles entity deaths.

    Notes
    -----
    This system runs every time step
    """

    def run(self, *args: Any, **kwargs: Any) -> None:
        current_date = self.world.get_resource(SimDateTime)
        event_log = self.world.get_resource(EventHandler)

        age_increment = float(self.elapsed_time.total_days) / DAYS_PER_YEAR

        character_comp: GameCharacter
        for guid, (character_comp, _, _) in self.world.get_components(
            GameCharacter, CanAge, Active
        ):
            character = self.world.get_gameobject(guid)

            life_stage_before = character_comp.life_stage
            character_comp.increment_age(age_increment)
            life_stage_after = character_comp.life_stage

            life_stage_changed = life_stage_before != life_stage_after

            if life_stage_changed is False:
                continue

            if character_comp.life_stage == LifeStage.Adolescent:
                event_log.record_event(
                    Event(
                        name="BecameAdolescent",
                        timestamp=current_date.to_iso_str(),
                        roles=[
                            EventRole("Character", character.uid),
                        ],
                    ),
                )

            elif character_comp.life_stage == LifeStage.YoungAdult:
                event_log.record_event(
                    Event(
                        name="BecomeYoungAdult",
                        timestamp=current_date.to_iso_str(),
                        roles=[
                            EventRole("Character", character.uid),
                        ],
                    ),
                )

            elif character_comp.life_stage == LifeStage.Adult:
                event_log.record_event(
                    Event(
                        name="BecomeAdult",
                        timestamp=current_date.to_iso_str(),
                        roles=[
                            EventRole("Character", character.uid),
                        ],
                    ),
                )

            elif character_comp.life_stage == LifeStage.Senior:
                event_log.record_event(
                    Event(
                        name="BecomeSenior",
                        timestamp=current_date.to_iso_str(),
                        roles=[
                            EventRole("Character", character.uid),
                        ],
                    ),
                )


class EventSystem(ISystem):
    def process(self, *args: Any, **kwargs: Any) -> None:
        event_log = self.world.get_resource(EventHandler)
        event_log.process_event_queue(self.world)


class UnemployedStatusSystem(System):
    years_to_find_a_job: float = 5.0

    def run(self, *args: Any, **kwargs: Any) -> None:
        for guid, unemployed in self.world.get_component(Unemployed):
            character = self.world.get_gameobject(guid)
            unemployed.years += self.elapsed_time.total_days / DAYS_PER_YEAR

            if unemployed.years >= self.years_to_find_a_job:
                spouses = get_relationships_with_statuses(character, Married)

                # Do not depart if one or more of the entity's spouses has a job
                if any(
                    [
                        self.world.get_gameobject(rel.target).has_component(Occupation)
                        for rel in spouses
                    ]
                ):
                    continue

                else:
                    characters_to_depart: List[GameObject] = [character]

                    # Have all spouses depart
                    # Allows for polygamy
                    for rel in spouses:
                        spouse = self.world.get_gameobject(rel.target)
                        if spouse.has_component(Active):
                            characters_to_depart.append(spouse)

                    # Have all children living in the same house depart
                    children = get_relationships_with_statuses(character, ParentOf)
                    for rel in children:
                        child = self.world.get_gameobject(rel.target)
                        if child.has_component(Active) and check_share_residence(
                            character, child
                        ):
                            characters_to_depart.append(child)

                    for c in characters_to_depart:
                        add_status(c, Departed())
                        remove_status(c, Active)

                    remove_status(character, Unemployed)

                    event = orrery.events.DepartEvent(
                        self.world.get_resource(SimDateTime),
                        characters_to_depart,
                        "unemployment",
                    )

                    self.world.get_resource(EventHandler).record_event(event)


class PregnantStatusSystem(System):
    def run(self, *args: Any, **kwargs: Any) -> None:
        current_date = self.world.get_resource(SimDateTime)

        for guid, pregnant in self.world.get_component(Pregnant):
            character = self.world.get_gameobject(guid)

            if pregnant.due_date <= current_date:
                continue

            other_parent = self.world.get_gameobject(pregnant.partner_id)

            baby = create_character(
                self.world,
                generate_child_bundle(
                    self.world,
                    character,
                    other_parent,
                ),
                last_name=character.get_component(GameCharacter).last_name,
            )

            set_residence(
                self.world,
                baby,
                self.world.get_gameobject(character.get_component(Resident).residence),
            )

            # Birthing parent to child
            add_relationship(character, baby)
            add_relationship_status(character, baby, ParentOf())

            # Child to birthing parent
            add_relationship(baby, character)
            add_relationship_status(baby, character, ChildOf())

            # Other parent to child
            add_relationship(other_parent, baby)
            add_relationship_status(other_parent, baby, ParentOf())

            # Child to other parent
            add_relationship(baby, other_parent)
            add_relationship_status(baby, other_parent, ChildOf())

            # Create relationships with children of birthing parent
            for rel in get_relationships_with_statuses(character, ParentOf):
                if rel.target == baby.uid:
                    continue

                sibling = self.world.get_gameobject(rel.target)

                # Baby to sibling
                add_relationship(baby, sibling)
                add_relationship_status(baby, sibling, SiblingOf())

                # Sibling to baby
                add_relationship(sibling, baby)
                add_relationship_status(sibling, baby, SiblingOf())

            # Create relationships with children of other parent
            for rel in get_relationships_with_statuses(other_parent, ParentOf):
                if rel.target == baby.uid:
                    continue

                sibling = self.world.get_gameobject(rel.target)

                # Baby to sibling
                add_relationship(baby, sibling)
                add_relationship_status(baby, sibling, SiblingOf())

                # Sibling to baby
                add_relationship(sibling, baby)
                add_relationship_status(sibling, baby, SiblingOf())

            remove_status(character, Pregnant)

            # Pregnancy event dates are retro-fit to be the actual date that the
            # child was due.
            self.world.get_resource(EventHandler).record_event(
                orrery.events.ChildBirthEvent(
                    current_date, character, other_parent, baby
                )
            )


class MarriedStatusSystem(System):
    def run(self, *args: Any, **kwargs: Any) -> None:
        for guid, married in self.world.get_component(Married):
            married.years += self.elapsed_time.total_days / DAYS_PER_YEAR


class DatingStatusSystem(System):
    def run(self, *args: Any, **kwargs: Any) -> None:
        for guid, dating in self.world.get_component(Dating):
            dating.years += self.elapsed_time.total_days / DAYS_PER_YEAR


class RelationshipUpdateSystem(System):
    """Increases the elapsed time for all statuses by one month"""

    def run(self, *args: Any, **kwargs: Any):
        for _, relationship in self.world.get_component(Relationship):
            # Update stats
            for _, stat in relationship:
                if stat.changes_with_time:
                    stat += round(
                        max(0, relationship.interaction_score.get_raw_value())
                        * lerp(-3, 3, stat.get_normalized_value())
                    )


class MarkUnemployedNewCharactersSystem(System):
    def run(self, *args: Any, **kwargs: Any) -> None:
        for guid in self.world.get_added_component(CurrentSettlement):
            gameobject = self.world.get_gameobject(guid)
            if game_character := gameobject.try_component(GameCharacter):
                if game_character.life_stage >= LifeStage.YoungAdult:
                    add_status(gameobject, InTheWorkforce())
                    if not gameobject.has_component(Occupation):
                        add_status(gameobject, Unemployed())


class RemoveFrequentedFromDepartedSystem(System):
    def run(self, *args: Any, **kwargs: Any) -> None:
        for guid in self.world.get_added_component(Departed):
            gameobject = self.world.get_gameobject(guid)
            if gameobject.has_component(GameCharacter):
                clear_frequented_locations(gameobject)
