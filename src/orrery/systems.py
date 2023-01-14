import random
from abc import abstractmethod
from collections import Counter
from typing import Any, List, Optional, cast

import orrery.events
from orrery.components.business import (
    Business,
    BusinessLibrary,
    InTheWorkforce,
    Occupation,
    OccupationType,
    OccupationTypeLibrary,
    OpenForBusiness,
)
from orrery.components.character import (
    CanAge,
    CharacterLibrary,
    GameCharacter,
    LifeStage,
)
from orrery.components.relationship_status import Married
from orrery.components.residence import Residence, ResidenceLibrary, Vacant
from orrery.components.shared import Active, Building, FrequentedLocations, Location
from orrery.core.config import CharacterConfig, OrreryConfig
from orrery.core.ecs import ComponentBundle, GameObject, ISystem
from orrery.core.event import Event, EventHandler, EventRole
from orrery.core.life_event import LifeEventLibrary
from orrery.core.query import QueryBuilder
from orrery.core.relationship import RelationshipManager, RelationshipTag, lerp
from orrery.core.settlement import Settlement
from orrery.core.status import StatusManager
from orrery.core.time import DAYS_PER_YEAR, SimDateTime, TimeDelta
from orrery.statuses import Unemployed
from orrery.utils.common import (
    add_business,
    add_character_to_settlement,
    add_residence,
    create_business,
    create_character,
    create_residence,
    set_residence,
    start_job,
)
from orrery.utils.relationships import (
    add_relationship,
    add_relationship_status,
    get_relationship,
)
from orrery.utils.statuses import has_status


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


class LifeEventSystem(System):
    """Fires LifeEvents adding some spice to the simulation data"""

    def __init__(self, interval: Optional[TimeDelta] = None) -> None:
        super().__init__(interval=interval)

    def run(self, *args: Any, **kwarg: Any) -> None:
        """Simulate LifeEvents for characters"""
        rng = self.world.get_resource(random.Random)
        life_events = self.world.get_resource(LifeEventLibrary)

        for _, settlement in self.world.get_component(Settlement):
            for life_event in rng.choices(life_events.get_all(), k=10):
                success = life_event.try_execute_event(self.world)
                if success:
                    self.world.clear_command_queue()


class MeetNewPeopleSystem(ISystem):
    """
    Characters add new people to their social network
    based on places that they frequent
    """

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
                    if other_id != gid:
                        candidates.append(other_id)

            if candidates:
                candidate_weights = Counter(candidates)

                # Select one randomly
                options, weights = zip(*candidate_weights.items())

                rng = self.world.get_resource(random.Random)

                acquaintance_id = rng.choices(options, weights=weights, k=1)[0]

                if acquaintance_id not in character.get_component(RelationshipManager):
                    acquaintance = self.world.get_gameobject(acquaintance_id)

                    add_relationship(character, acquaintance)
                    add_relationship(acquaintance, character)

                    # Calculate interaction scores
                    get_relationship(character, acquaintance).interaction_score += 1
                    get_relationship(acquaintance, character).interaction_score += 1


class FindEmployeesSystem(ISystem):
    """Finds employees to work open positions at businesses"""

    def process(self, *args: Any, **kwargs: Any) -> None:
        date = self.world.get_resource(SimDateTime)
        event_log = self.world.get_resource(EventHandler)
        occupation_types = self.world.get_resource(OccupationTypeLibrary)
        rng = self.world.get_resource(random.Random)

        for _, (business, _) in self.world.get_components(Business, OpenForBusiness):
            business = cast(Business, business)
            open_positions = business.get_open_positions()

            for occupation_name in open_positions:
                occupation_type = occupation_types.get(occupation_name)

                candidate_query = (
                    QueryBuilder(occupation_name)
                    .with_((InTheWorkforce, Active))
                    .filter_(
                        lambda world, *gameobjects: has_status(
                            gameobjects[0], Unemployed
                        )
                    )
                )

                if occupation_type.precondition:
                    candidate_query.filter_(occupation_type.precondition)

                candidate_list = candidate_query.build().execute(self.world)

                if not candidate_list:
                    continue

                candidate = self.world.get_gameobject(rng.choice(candidate_list)[0])

                occupation = Occupation(
                    occupation_type=occupation_name,
                    business=business.gameobject.uid,
                    level=occupation_type.level,
                )

                start_job(business, candidate, occupation)

                event_log.record_event(
                    orrery.events.StartJobEvent(
                        date,
                        business=business.gameobject,
                        character=candidate,
                        occupation=occupation_name,
                    )
                )


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
    """
    Build a new business building at a random free space on the land grid.
    """

    def find_business_owner(
        self, occupation_type: OccupationType
    ) -> Optional[GameObject]:
        """Find someone to run the new business"""
        rng = self.world.get_resource(random.Random)

        query_builder = (
            QueryBuilder()
            .with_((InTheWorkforce, Active))
            .filter_(lambda world, *gameobjects: has_status(gameobjects[0], Unemployed))
        )

        if occupation_type.precondition:
            query_builder.filter_(occupation_type.precondition)

        q = query_builder.build()

        candidate_list = q.execute(self.world)

        if candidate_list:
            return self.world.get_gameobject(rng.choice(candidate_list)[0])

        return None

    def process(self, *args: Any, **kwargs: Any) -> None:
        """Build a new business when there is space"""
        event_log = self.world.get_resource(EventHandler)
        business_library = self.world.get_resource(BusinessLibrary)
        occupation_types = self.world.get_resource(OccupationTypeLibrary)
        rng = self.world.get_resource(random.Random)

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

            if bundle is None:
                return

            business_config = business_library.get(bundle.name)

            if business_config.owner_type is not None:
                owner_occupation_type = occupation_types.get(business_config.owner_type)
                owner = self.find_business_owner(owner_occupation_type)

                if owner is None:
                    continue

                business = add_business(
                    create_business(self.world, bundle),
                    self.world.get_gameobject(settlement_id),
                    lot=lot,
                )

                owner.add_component(
                    Occupation(
                        occupation_type=owner_occupation_type.name,
                        business=business.uid,
                        level=owner_occupation_type.level,
                    )
                )

                event_log.record_event(
                    orrery.events.StartBusinessEvent(
                        self.world.get_resource(SimDateTime),
                        owner,
                        business,
                        owner.get_component(Occupation).occupation_type,
                        business.get_component(Business).name,
                    )
                )

            else:
                business = add_business(
                    create_business(self.world, bundle),
                    self.world.get_gameobject(settlement_id),
                    lot=lot,
                )

                print(
                    f"Built new business ({business.uid}) {business.get_component(Business).name}"
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

        for _, (residence, _, _, _) in self.world.get_components(
            Residence, Building, Active, Vacant
        ):
            residence = cast(Residence, residence)

            settlement = self.world.get_gameobject(residence.settlement)

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

            add_character_to_settlement(self.world, character, settlement)
            set_residence(self.world, character, residence.gameobject, True)

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
                add_character_to_settlement(self.world, spouse, settlement)
                set_residence(self.world, spouse, residence.gameobject, True)

                # Configure relationship from character to spouse
                add_relationship(character, spouse)
                get_relationship(character, spouse).add_tags(
                    RelationshipTag.SignificantOther | RelationshipTag.Spouse
                )
                add_relationship_status(character, spouse, Married())
                get_relationship(character, spouse)["Romance"] += 45
                get_relationship(character, spouse)["Friendship"] += 30

                # Configure relationship from spouse to character
                add_relationship(spouse, character)
                get_relationship(spouse, character).add_tags(
                    RelationshipTag.SignificantOther | RelationshipTag.Spouse
                )
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
                    add_character_to_settlement(self.world, child, settlement)
                    set_residence(self.world, child, residence.gameobject)

                    children.append(child)

                    # Relationship of child to character
                    add_relationship(child, character)
                    get_relationship(child, character).add_tags(
                        RelationshipTag.Parent | RelationshipTag.Family
                    )
                    get_relationship(child, character)["Friendship"] += 20

                    # Relationship of character to child
                    add_relationship(character, child)
                    get_relationship(character, child).add_tags(
                        RelationshipTag.Child | RelationshipTag.Family
                    )
                    get_relationship(character, child)["Friendship"] += 20

                    if spouse:
                        # Relationship of child to spouse
                        add_relationship(child, spouse)
                        get_relationship(child, spouse).add_tags(
                            RelationshipTag.Parent | RelationshipTag.Family
                        )
                        get_relationship(child, spouse)["Friendship"] += 20

                        # Relationship of spouse to child
                        add_relationship(spouse, child)
                        add_relationship(spouse, child)
                        get_relationship(spouse, child).add_tags(
                            RelationshipTag.Child | RelationshipTag.Family
                        )
                        get_relationship(spouse, child)["Friendship"] += 20

                    for sibling in children:
                        # Relationship of child to sibling
                        add_relationship(child, sibling)
                        child.get_component(RelationshipManager).get(
                            sibling.uid
                        ).add_tags(RelationshipTag.Sibling)
                        child.get_component(RelationshipManager).get(
                            sibling.uid
                        ).add_tags(RelationshipTag.Family)
                        child.get_component(RelationshipManager).get(sibling.uid)[
                            "Friendship"
                        ] += 20

                        # Relationship of sibling to child
                        add_relationship(sibling, child)
                        sibling.get_component(RelationshipManager).get(
                            child.uid
                        ).add_tags(RelationshipTag.Sibling)
                        sibling.get_component(RelationshipManager).get(
                            child.uid
                        ).add_tags(RelationshipTag.Family)
                        sibling.get_component(RelationshipManager).get(child.uid)[
                            "Friendship"
                        ] += 20

            # Record a life event
            event_logger.record_event(
                orrery.events.MoveIntoTownEvent(
                    date, residence.gameobject, *generated_characters
                )
            )


class BusinessUpdateSystem(System):
    def run(self, *args: Any, **kwargs: Any) -> None:
        time_increment = float(self.elapsed_time.total_days) / DAYS_PER_YEAR
        for _, (business, _) in self.world.get_components(Business, OpenForBusiness):
            business = cast(Business, business)
            # Increment how long the business has been open for business
            business.years_in_business += time_increment


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

        for _, (character, _, _) in self.world.get_components(
            GameCharacter, CanAge, Active
        ):
            character = cast(GameCharacter, character)

            life_stage_before = character.life_stage
            character.increment_age(age_increment)
            life_stage_after = character.life_stage

            life_stage_changed = life_stage_before != life_stage_after

            if life_stage_changed is False:
                continue

            if character.life_stage == LifeStage.Adolescent:
                event_log.record_event(
                    Event(
                        name="BecameAdolescent",
                        timestamp=current_date.to_iso_str(),
                        roles=[
                            EventRole("Character", character.gameobject.uid),
                        ],
                    ),
                )

            elif character.life_stage == LifeStage.YoungAdult:
                event_log.record_event(
                    Event(
                        name="BecomeYoungAdult",
                        timestamp=current_date.to_iso_str(),
                        roles=[
                            EventRole("Character", character.gameobject.uid),
                        ],
                    ),
                )

            elif character.life_stage == LifeStage.Adult:
                event_log.record_event(
                    Event(
                        name="BecomeAdult",
                        timestamp=current_date.to_iso_str(),
                        roles=[
                            EventRole("Character", character.gameobject.uid),
                        ],
                    ),
                )

            elif character.life_stage == LifeStage.Senior:
                event_log.record_event(
                    Event(
                        name="BecomeSenior",
                        timestamp=current_date.to_iso_str(),
                        roles=[
                            EventRole("Character", character.gameobject.uid),
                        ],
                    ),
                )


class EventSystem(ISystem):
    def process(self, *args: Any, **kwargs: Any) -> None:
        event_log = self.world.get_resource(EventHandler)
        event_log.process_event_queue(self.world)


class StatusUpdateSystem(System):
    """Increases the elapsed time for all statuses by one month"""

    def run(self, *args: Any, **kwargs: Any):
        for guid, status_manager in self.world.get_component(StatusManager):
            gameobject = self.world.get_gameobject(guid)
            for status in status_manager:
                status.on_update(self.world, gameobject, self.elapsed_time)


class RelationshipUpdateSystem(System):
    """Increases the elapsed time for all statuses by one month"""

    def run(self, *args: Any, **kwargs: Any):
        for guid, relationship_manager in self.world.get_component(RelationshipManager):
            gameobject = self.world.get_gameobject(guid)
            for relationship in relationship_manager:
                # Update stats
                for _, stat in relationship:
                    if stat.changes_with_time:
                        stat += round(
                            max(0, relationship.interaction_score.get_raw_value())
                            * lerp(-3, 3, stat.get_normalized_value())
                        )
                # Update statuses
                for status in relationship.get_statuses():
                    status.on_update(
                        self.world, gameobject, relationship, self.elapsed_time
                    )
