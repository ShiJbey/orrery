import random
from abc import ABC, abstractmethod
from collections import Counter
from typing import Any, List, Optional

import orrery.events
from orrery.components.business import (
    Business,
    InTheWorkforce,
    Occupation,
    OccupationType,
    OpenForBusiness,
    Unemployed,
)
from orrery.components.character import (
    CanAge,
    ChildOf,
    Dating,
    Departed,
    GameCharacter,
    LifeStage,
    Married,
    ParentOf,
    Pregnant,
    SiblingOf,
)
from orrery.components.relationship import Relationship, lerp
from orrery.components.residence import Residence, Resident, Vacant
from orrery.components.settlement import Settlement
from orrery.components.shared import (
    Active,
    Building,
    CurrentSettlement,
    FrequentedBy,
    FrequentedLocations,
)
from orrery.config import CharacterConfig, OrreryConfig
from orrery.content_management import (
    BusinessLibrary,
    CharacterLibrary,
    LifeEventLibrary,
    OccupationTypeLibrary,
    ResidenceLibrary,
)
from orrery.core.ai import AIComponent
from orrery.core.ecs import GameObject, ISystem
from orrery.core.ecs.ecs import SystemGroup
from orrery.core.event import AllEvents, EventBuffer
from orrery.core.time import DAYS_PER_YEAR, SimDateTime, TimeDelta
from orrery.prefabs import CharacterPrefab
from orrery.utils.common import (
    add_business_to_settlement,
    add_character_to_settlement,
    add_residence,
    check_share_residence,
    clear_frequented_locations,
    create_residence,
    end_job,
    generate_child_prefab,
    set_frequented_locations,
    set_residence,
    spawn_business,
    spawn_character,
    start_job,
)
from orrery.utils.relationships import (
    add_relationship,
    add_relationship_status,
    get_relationship,
    get_relationships_with_statuses,
    has_relationship,
    reevaluate_social_rules,
)
from orrery.utils.statuses import add_status, clear_statuses, remove_status


class InitializationSystemGroup(SystemGroup):
    """A group of systems that runs"""

    group_name = "initialization"
    priority = 99999

    def process(self, *args: Any, **kwargs: Any) -> None:
        super().process(*args, **kwargs)
        self.world.remove_system(type(self))


class EarlyCharacterUpdateSystemGroup(SystemGroup):
    """The first phase of character updates"""

    group_name = "early-character-update"
    sys_group = "character-update"
    priority = 99999


class CharacterUpdateSystemGroup(SystemGroup):
    """The phase of character updates"""

    group_name = "character-update"


class LateCharacterUpdateSystemGroup(SystemGroup):
    """The last phase of character updates"""

    group_name = "late-character-update"
    sys_group = "character-update"
    priority = -99999


class BusinessUpdateSystemGroup(SystemGroup):
    """The phase of character updates"""

    group_name = "business-update"


class CoreSystemsSystemGroup(SystemGroup):
    group_name = "core-systems"


class RelationshipUpdateSystemGroup(SystemGroup):
    group_name = "relationship-update"


class StatusUpdateSystemGroup(SystemGroup):
    group_name = "status-update"


class EventListenersSystemGroup(SystemGroup):
    group_name = "event-listeners"


class DataCollectionSystemGroup(SystemGroup):
    sys_group = "core-systems"
    priority = -99998
    group_name = "data-collection"


class CleanUpSystemGroup(SystemGroup):
    """Group of systems that clean-up residual data before the next step"""

    group_name = "clean-up"
    priority = -99999


class System(ISystem, ABC):
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
        self._next_run: SimDateTime = SimDateTime(1, 1, 1) + self._interval
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

    # The time system should be the last system to run every step. There's always the
    # possibility that a system may need to record the current date. So, we don't want
    # the date changing before all other systems have run.
    sys_group = "root"
    priority = -99999

    def process(self, *args: Any, **kwargs: Any) -> None:
        # Get time increment from the simulation configuration
        # this may be slow, but it is the cleanest configuration thus far
        increment = self.world.get_resource(OrreryConfig).time_increment
        current_date = self.world.get_resource(SimDateTime)
        current_date.increment(months=increment)


class LifeEventSystem(System):
    """This system attempts to fire random life events"""

    sys_group = "character-update"

    def run(self, *args: Any, **kwarg: Any) -> None:
        """Simulate LifeEvents for characters"""
        life_events = self.world.get_resource(LifeEventLibrary)
        all_events = life_events.get_all()

        # for guid, (_, _, life_event_queue) in self.world.get_components(
        #     (GameCharacter, Active, LifeEventQueue)
        # ):
        #     character = self.world.get_gameobject(guid)
        #
        #     # Go through all the life events and queue the ones that pass
        #     for life_event in all_events:
        #         event_instance = life_event.instantiate(
        #             self.world,
        #             bindings={life_event.get_initiator_role(): character.uid},
        #         )
        #
        #         if event_instance:
        #             life_event_queue.push(event_instance)
        #
        #     if len(life_event_queue):
        #         chosen_event: LifeEventInstance = self.world.get_resource(
        #             random.Random
        #         ).choice(list(life_event_queue.__iter__()))
        #         chosen_event.execute()
        #         life_event_queue.clear()


class MeetNewPeopleSystem(ISystem):
    """Characters meet new people based on places they frequent"""

    sys_group = "character-update"

    def process(self, *args: Any, **kwargs: Any):
        for gid, _ in self.world.get_components((GameCharacter, Active)):
            character = self.world.get_gameobject(gid)

            frequented_locations = character.get_component(
                FrequentedLocations
            ).locations

            candidates: List[int] = []

            for loc_id in frequented_locations:
                for other_id in self.world.get_gameobject(loc_id).get_component(
                    FrequentedBy
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
                options, weights = tuple(zip(*candidate_weights.items()))  # type: ignore

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

    sys_group = "core-systems"

    def process(self, *args: Any, **kwargs: Any) -> None:
        occupation_types = self.world.get_resource(OccupationTypeLibrary)
        rng = self.world.get_resource(random.Random)

        for guid, (business, _) in self.world.get_components(
            (Business, OpenForBusiness)
        ):
            open_positions = business.get_open_positions()

            for occupation_name in open_positions:
                occupation_type = occupation_types.get(occupation_name)

                candidates = [
                    self.world.get_gameobject(g)
                    for g, _ in self.world.get_components(
                        (InTheWorkforce, Active, Unemployed)
                    )
                ]

                if occupation_type.precondition:
                    candidates = filter(occupation_type.precondition, candidates)

                if not candidates:
                    continue

                candidate = rng.choice(candidates)

                start_job(candidate, self.world.get_gameobject(guid), occupation_name)


class BuildHousingSystem(ISystem):
    """
    Builds housing on unoccupied spaces on the land grid
    """

    sys_group = "core-systems"

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

            prefab = residence_library.choose_random(rng)

            if prefab is None:
                continue

            add_residence(
                create_residence(self.world, prefab),
                settlement=self.world.get_gameobject(settlement_id),
                lot=lot,
            )


class BuildBusinessSystem(ISystem):
    """Build a new business building at a random free space on the land grid."""

    sys_group = "core-systems"

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

        candidates = [
            self.world.get_gameobject(g)
            for g, _ in self.world.get_components((InTheWorkforce, Active, Unemployed))
        ]

        if occupation_type.precondition:
            candidates = filter(occupation_type.precondition, candidates)

        if not candidates:
            return None

        # NOTE: It might be nice to eventually swap this out for a
        # selection strategy that scores the characters based on
        # who is most likely to take on this role
        candidate = rng.choice(candidates)

        return candidate

    def process(self, *args: Any, **kwargs: Any) -> None:
        """Attempt to build one new business per settlement"""

        event_log = self.world.get_resource(EventBuffer)
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
            prefab = business_library.choose_random(
                self.world, self.world.get_gameobject(settlement_id)
            )

            # Return early if none of the businesses entries' preconditions
            # are satisfied
            if prefab is None:
                return

            if prefab.config.owner_type is not None:
                owner_occupation_type = occupation_types.get(prefab.config.owner_type)
                owner = self.find_business_owner(owner_occupation_type)

                if owner is None:
                    continue

                business = spawn_business(self.world, prefab)

                add_business_to_settlement(
                    business,
                    self.world.get_gameobject(settlement_id),
                    lot_id=lot,
                )

                event_log.append(
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
                business = spawn_business(self.world, prefab)

                add_business_to_settlement(
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

    sys_group = "core-systems"

    __slots__ = "chance_spawn"

    def __init__(
        self,
        chance_spawn: float = 0.5,
        interval: Optional[TimeDelta] = None,
    ) -> None:
        super().__init__(interval=interval)
        self.chance_spawn: float = chance_spawn

    @staticmethod
    def _try_get_spouse_prefab(
        rng: random.Random,
        character_config: CharacterConfig,
        character_library: CharacterLibrary,
    ) -> Optional[CharacterPrefab]:
        if rng.random() < character_config.spawning.chance_spawn_with_spouse:
            # Create another character to be their spouse
            potential_spouse_prefabs = character_library.get_matching_prefabs(
                *character_config.spawning.spouse_archetypes
            )

            if potential_spouse_prefabs:
                return rng.choice(potential_spouse_prefabs)

        return None

    def run(self, *args: Any, **kwargs: Any) -> None:
        rng = self.world.get_resource(random.Random)
        date = self.world.get_resource(SimDateTime)
        event_logger = self.world.get_resource(EventBuffer)
        character_library = self.world.get_resource(CharacterLibrary)

        for guid, (_, _, _, _, current_settlement,) in self.world.get_components(
            (Residence, Building, Active, Vacant, CurrentSettlement)
        ):
            residence = self.world.get_gameobject(guid)

            settlement = self.world.get_gameobject(current_settlement.settlement)

            # Return early if the random-roll is not sufficient
            if rng.random() > self.chance_spawn:
                return

            prefab = character_library.choose_random(rng)

            # There are no archetypes available to spawn
            if prefab is None:
                return

            # Track all the characters generated
            generated_characters: List[GameObject] = []

            # Create a new entity using the archetype

            character = spawn_character(
                self.world, prefab, life_stage=LifeStage.YoungAdult
            )

            generated_characters.append(character)

            character_config = character.get_component(GameCharacter).config

            add_character_to_settlement(character, settlement)
            set_residence(self.world, character, residence, True)

            spouse: Optional[GameObject] = None

            spouse_prefab = self._try_get_spouse_prefab(
                rng, character_config, character_library
            )

            if spouse_prefab:
                spouse = spawn_character(
                    self.world,
                    spouse_prefab,
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

            potential_child_prefabs = character_library.get_matching_prefabs(
                *character_config.spawning.child_archetypes
            )

            if potential_child_prefabs:
                chosen_child_prefabs = rng.sample(potential_child_prefabs, num_kids)

                for child_prefab in chosen_child_prefabs:
                    child = spawn_character(
                        self.world,
                        child_prefab,
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
            event_logger.append(
                orrery.events.MoveIntoTownEvent(date, residence, *generated_characters)
            )


class BusinessUpdateSystem(System):
    sys_group = "business-update"

    def run(self, *args: Any, **kwargs: Any) -> None:
        time_increment = float(self.elapsed_time.total_days) / DAYS_PER_YEAR
        business: Business
        for _, (business, _) in self.world.get_components((Business, OpenForBusiness)):
            # Increment how long the business has been open for business
            business.years_in_business += time_increment


class OccupationUpdateSystem(System):
    sys_group = "character-update"

    def run(self, *args: Any, **kwargs: Any) -> None:
        for _, occupation in self.world.get_component(Occupation):
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

    sys_group = "character-update"

    def run(self, *args: Any, **kwargs: Any) -> None:
        current_date = self.world.get_resource(SimDateTime)
        event_log = self.world.get_resource(EventBuffer)

        age_increment = float(self.elapsed_time.total_days) / DAYS_PER_YEAR

        for guid, (character_comp, _, _) in self.world.get_components(
            (GameCharacter, CanAge, Active)
        ):
            character = self.world.get_gameobject(guid)

            life_stage_before = character_comp.life_stage
            character_comp.increment_age(age_increment)
            life_stage_after = character_comp.life_stage

            life_stage_changed = life_stage_before != life_stage_after

            if life_stage_changed is False:
                continue

            if character_comp.life_stage == LifeStage.Adolescent:
                event_log.append(
                    orrery.events.BecomeAdolescentEvent(current_date, character)
                )

            elif character_comp.life_stage == LifeStage.YoungAdult:
                event_log.append(
                    orrery.events.BecomeYoungAdultEvent(current_date, character)
                )

            elif character_comp.life_stage == LifeStage.Adult:
                event_log.append(
                    orrery.events.BecomeAdultEvent(current_date, character)
                )

            elif character_comp.life_stage == LifeStage.Senior:
                event_log.append(
                    orrery.events.BecomeSeniorEvent(current_date, character)
                )


class EventSystem(ISystem):
    sys_group = "clean-up"
    priority = -9999

    def process(self, *args: Any, **kwargs: Any) -> None:
        event_log = self.world.get_resource(EventBuffer)
        all_events = self.world.get_resource(AllEvents)
        for event in event_log.iter_events():
            all_events.append(event)
        event_log.clear()


class UnemployedStatusSystem(System):
    sys_group = "status-update"
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

                    self.world.get_resource(EventBuffer).append(event)


class PregnantStatusSystem(System):
    sys_group = "status-update"

    def run(self, *args: Any, **kwargs: Any) -> None:
        current_date = self.world.get_resource(SimDateTime)

        for guid, pregnant in self.world.get_component(Pregnant):
            character = self.world.get_gameobject(guid)

            if pregnant.due_date <= current_date:
                continue

            other_parent = self.world.get_gameobject(pregnant.partner_id)

            baby = spawn_character(
                self.world,
                generate_child_prefab(
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
            self.world.get_resource(EventBuffer).append(
                orrery.events.ChildBirthEvent(
                    current_date, character, other_parent, baby
                )
            )


class MarriedStatusSystem(System):
    sys_group = "status-update"

    def run(self, *args: Any, **kwargs: Any) -> None:
        for _, married in self.world.get_component(Married):
            married.years += self.elapsed_time.total_days / DAYS_PER_YEAR


class DatingStatusSystem(System):
    sys_group = "status-update"

    def run(self, *args: Any, **kwargs: Any) -> None:
        for _, dating in self.world.get_component(Dating):
            dating.years += self.elapsed_time.total_days / DAYS_PER_YEAR


class RelationshipUpdateSystem(System):
    """Increases the elapsed time for all statuses by one month"""

    sys_group = "relationship-update"

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
    sys_group = "late-character-update"

    def run(self, *args: Any, **kwargs: Any) -> None:
        for guid in self.world.iter_added_component(CurrentSettlement):
            gameobject = self.world.get_gameobject(guid)
            if game_character := gameobject.try_component(GameCharacter):
                if game_character.life_stage >= LifeStage.YoungAdult:
                    add_status(gameobject, InTheWorkforce())
                    if not gameobject.has_component(Occupation):
                        add_status(gameobject, Unemployed())


class RemoveFrequentedFromDepartedSystem(System):
    sys_group = "late-character-update"

    def run(self, *args: Any, **kwargs: Any) -> None:
        for guid in self.world.iter_added_component(Departed):
            gameobject = self.world.get_gameobject(guid)
            if gameobject.has_component(GameCharacter):
                clear_frequented_locations(gameobject)


class OnDepartSystem(ISystem):
    sys_group = "event-listeners"

    def process(self, *args: Any, **kwargs: Any) -> None:

        for event in self.world.get_resource(EventBuffer).iter_events_of_type(
            orrery.events.DepartEvent
        ):
            for character in event.characters:
                remove_status(character, Active)
                add_status(character, Departed())
                clear_frequented_locations(character)
                clear_statuses(character)
                set_residence(self.world, character, None)

                if character.has_component(Occupation):
                    end_job(character, reason=event.get_type())


class OnDeathSystem(ISystem):
    sys_group = "event-listeners"

    def process(self, *args: Any, **kwargs: Any) -> None:

        for event in self.world.get_resource(EventBuffer).iter_events_of_type(
            orrery.events.DeathEvent
        ):
            set_residence(self.world, event.character, None)
            clear_statuses(event.character)


class OnJoinSettlementSystem(ISystem):
    sys_group = "event-listeners"

    def process(self, *args: Any, **kwargs: Any) -> None:

        for event in self.world.get_resource(EventBuffer).iter_events_of_type(
            orrery.events.JoinSettlementEvent
        ):
            game_character = event.character.get_component(GameCharacter)

            if game_character.life_stage >= LifeStage.YoungAdult:
                add_status(event.character, InTheWorkforce())
                if not event.character.has_component(Occupation):
                    add_status(event.character, Unemployed())


class RemoveRetiredFromOccupationSystem(ISystem):
    sys_group = "event-listeners"

    def process(self, *args: Any, **kwargs: Any) -> None:

        for event in self.world.get_resource(EventBuffer).iter_events_of_type(
            orrery.events.RetirementEvent
        ):
            if event.character.has_component(Occupation):
                end_job(event.character, reason=event.get_type())


class OnBecomeYoungAdultSystem(ISystem):

    sys_group = "event-listeners"

    def process(self, *args: Any, **kwargs: Any) -> None:

        for event in self.world.get_resource(EventBuffer).iter_events_of_type(
            orrery.events.BecomeYoungAdultEvent
        ):
            add_status(event.character, InTheWorkforce())

            if not event.character.has_component(Occupation):
                add_status(event.character, Unemployed())


class PrintEventBufferSystem(ISystem):

    sys_group = "clean-up"
    priority = -9998

    def process(self, *args: Any, **kwargs: Any) -> None:
        for event in self.world.get_resource(EventBuffer).iter_events():
            print(str(event))


class ReevaluateSocialRulesSystem(System):

    sys_group = "relationship-update"

    def run(self, *args: Any, **kwargs: Any) -> None:
        for guid, relationship_comp in self.world.get_component(Relationship):
            relationship = self.world.get_gameobject(guid)
            subject = self.world.get_gameobject(relationship_comp.owner)
            target = self.world.get_gameobject(relationship_comp.target)
            reevaluate_social_rules(relationship, subject, target)


class UpdateFrequentedLocationSystem(System):
    sys_group = "character-update"

    def run(self, *args: Any, **kwargs: Any) -> None:
        for guid, (_, current_settlement) in self.world.get_components(
            (FrequentedLocations, CurrentSettlement)
        ):
            character = self.world.get_gameobject(guid)
            set_frequented_locations(
                character,
                self.world.get_gameobject(current_settlement.settlement),
            )


class AIActionSystem(System):

    sys_group = "character-update"

    def run(self, *args: Any, **kwargs: Any) -> None:
        for guid, ai_component in self.world.get_component(AIComponent):
            gameobject = self.world.get_gameobject(guid)
            ai_component.execute_action(self.world, gameobject)
