import random
from collections import Counter
from abc import abstractmethod
from typing import Any, List, Optional, cast

from orrery.components.character import CanAge, CharacterLibrary, GameCharacter, LifeStage
from orrery.components.shared import FrequentedLocations, Location, Position2D
from orrery.components.residence import Residence, ResidenceLibrary, Vacant
from orrery.core.ecs import GameObject, ISystem
from orrery.core.query import QueryBuilder
from orrery.core.relationship import RelationshipManager, RelationshipTag
from orrery.events import MoveIntoTownEvent, StartJobEvent
from orrery.utils.common import add_relationship, get_relationship, set_residence, start_job
from orrery.core.time import DAYS_PER_YEAR, SimDateTime, TimeDelta
from orrery.components.settlement import Settlement
from orrery.core.life_event import LifeEventLibrary
from orrery.core.event import Event, EventLog, EventRole
from orrery.components.shared import Active, Building
from orrery.components.business import (
    Business,
    BusinessLibrary,
    InTheWorkforce,
    Occupation,
    OpenForBusiness,
    OccupationTypeLibrary,
)


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
    """
    Advances simulation time using a time increment
    """

    def process(self, *args: Any, **kwargs: Any) -> None:
        current_date = self.world.get_resource(SimDateTime)
        current_date.increment(months=1)


class LifeEventSystem(System):
    """
    LifeEventSimulator handles firing LifeEvents for characters
    and performing entity behaviors
    """

    def __init__(self, interval: Optional[TimeDelta] = None) -> None:
        super().__init__(interval=interval)

    def run(self, *args: Any, **kwarg: Any) -> None:
        """Simulate LifeEvents for characters"""
        settlement = self.world.get_resource(Settlement)
        rng = self.world.get_resource(random.Random)
        life_events = self.world.get_resource(LifeEventLibrary)

        for life_event in rng.choices(
            life_events.get_all(), k=(max(1, int(settlement.population / 2)))
        ):
            success = life_event.try_execute_event(self.world)
            if success:
                self.world.clear_command_queue()


class MeetNewPeopleSystem(ISystem):
    def process(self, *args: Any, **kwargs: Any):
        for gid, _ in self.world.get_component(GameCharacter):
            character = self.world.get_gameobject(gid)

            frequented_locations = character.get_component(
                FrequentedLocations
            ).locations

            candidates: List[int] = []

            for l in frequented_locations:
                for other_id in (
                    self.world.get_gameobject(l).get_component(Location).frequented_by
                ):
                    candidates.append(other_id)

            if candidates:
                candidate_weights = Counter(candidates)

                # Select one randomly
                options, weights = zip(*candidate_weights.items())

                rng = self.world.get_resource(random.Random)

                acquaintance_id = rng.choices(options, weights=weights, k=1)[0]

                if acquaintance_id not in character.get_component(RelationshipManager):
                    acquaintance = self.world.get_gameobject(acquaintance_id)

                    add_relationship(self.world, character, acquaintance)
                    add_relationship(self.world, acquaintance, character)

                    # Calculate interaction scores
                    get_relationship(
                        self.world, character, acquaintance
                    ).interaction_score += 1
                    get_relationship(
                        self.world, acquaintance, character
                    ).interaction_score += 1


class FindEmployeesSystem(ISystem):
    def process(self, *args: Any, **kwargs: Any) -> None:
        date = self.world.get_resource(SimDateTime)
        event_log = self.world.get_resource(EventLog)
        occupation_types = self.world.get_resource(OccupationTypeLibrary)
        rng = self.world.get_resource(random.Random)

        for _, (business, _, _, _) in self.world.get_components(
            Business, OpenForBusiness, Building, Active
        ):
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
                    business=business.gameobject.id,
                    level=occupation_type.level,
                )

                start_job(self.world, business, candidate, occupation)

                event_log.record_event(
                    StartJobEvent(
                        date,
                        business=business.gameobject,
                        character=candidate,
                        occupation=occupation_name,
                    )
                )


class BuildHousingSystem(System):
    """
    Builds housing archetypes on unoccupied spaces on the land grid

    Attributes
    ----------
    chance_of_build: float
        Probability that a new residential building will be built
        if there is space available
    """

    __slots__ = "chance_of_build"

    def __init__(
        self, chance_of_build: float = 0.5, interval: Optional[TimeDelta] = None
    ) -> None:
        super().__init__(interval=interval)
        self.chance_of_build: float = chance_of_build

    def run(self, *args: Any, **kwargs: Any) -> None:
        """Build a new residence when there is space"""
        settlement = self.world.get_resource(Settlement)
        rng = self.world.get_resource(random.Random)
        residence_library = self.world.get_resource(ResidenceLibrary)

        # Return early if the random-roll is not sufficient
        if rng.random() > self.chance_of_build:
            return

        vacancies = settlement.land_map.get_vacant_lots()

        # Return early if there is nowhere to build
        if len(vacancies) == 0:
            return

        # Don't build more housing if 60% of the land is used for residential buildings
        if len(vacancies) / float(settlement.land_map.get_total_lots()) < 0.4:
            return

        # Pick a random lot from those available
        lot = rng.choice(vacancies)

        archetype = residence_library.choose_random(rng)

        if archetype is None:
            return None

        # Construct a random residence archetype
        residence = archetype.spawn(self.world)

        # Reserve the space
        settlement.land_map.reserve_lot(lot, residence.id)

        # Set the position of the building
        position = settlement.land_map.get_lot_position(lot)
        residence.add_component(Position2D(position[0], position[1]))
        residence.add_component(Building(building_type="residential", lot=lot))
        residence.add_component(Active())
        residence.add_component(Vacant())


class BuildBusinessSystem(System):
    """
    Build a new business building at a random free space on the land grid.

    Attributes
    ----------
    chance_of_build: float
        The probability that a new business may be built this timestep
    """

    __slots__ = "chance_of_build"

    def __init__(
        self, chance_of_build: float = 0.5, interval: Optional[TimeDelta] = None
    ) -> None:
        super().__init__(interval)
        self.chance_of_build: float = chance_of_build

    def find_business_owner(self, business: Business):
        """Find someone to run the new business"""
        rng = self.world.get_resource(random.Random)

        if business.owner_type is None:
            return None

        occupation_type = occupation_types.get(business.owner_type)

        result = fill_open_position(self.world, occupation_type, business, rng)

        if result:
            candidate, occupation = result

            start_job(
                self.world,
                business,
                candidate,
                occupation,
                is_owner=True,
            )

            return candidate

        return None

    def run(self, *args: Any, **kwargs: Any) -> None:
        """Build a new business when there is space"""
        settlement = self.world.get_resource(Settlement)
        event_log = self.world.get_resource(EventLog)
        business_library = self.world.get_resource(BusinessLibrary)
        rng = self.world.get_resource(random.Random)

        # Return early if the random-roll is not sufficient
        if rng.random() > self.chance_of_build:
            return

        vacancies = settlement.land_map.get_vacant_lots()

        # Return early if there is nowhere to build
        if len(vacancies) == 0:
            return

        # Pick a random lot from those available
        lot = rng.choice(vacancies)

        # Pick random eligible business archetype
        archetype = business_library.choose_random(self.world)

        if archetype is None:
            return

        # Build a random business archetype
        business = archetype.spawn(self.world)

        # Attempt to find an owner
        if business.get_component(Business).needs_owner():
            owner = self.find_business_owner(business.get_component(Business))

            if owner is None:
                return

            event_log.record_event(
                StartBusinessEvent(
                    self.world.get_resource(SimDateTime),
                    owner,
                    business,
                    owner.get_component(Occupation).occupation_type,
                    business.get_component(Business).name,
                )
            )

        # Reserve the space
        settlement.land_map.reserve_lot(lot, business.id)

        # Set the position of the building
        position = settlement.land_map.get_lot_position(lot)
        business.get_component(Position2D).x = position[0]
        business.get_component(Position2D).y = position[1]

        # Give the business a building
        business.add_component(Building(building_type="commercial", lot=lot))
        business.add_component(OpenForBusiness())
        business.add_component(Active())


class SpawnResidentSystem(System):
    """Adds new characters to the simulation"""

    __slots__ = "chance_spawn"

    def __init__(
        self,
        chance_spawn: float = 0.5,
        interval: Optional[TimeDelta] = None,
    ) -> None:
        super().__init__(interval=interval)
        self.chance_spawn: float = chance_spawn

    def run(self, *args: Any, **kwargs: Any) -> None:
        rng = self.world.get_resource(random.Random)
        date = self.world.get_resource(SimDateTime)
        settlement = self.world.get_resource(Settlement)
        event_logger = self.world.get_resource(EventLog)
        character_library = self.world.get_resource(CharacterLibrary)

        for _, (residence, _, _, _) in self.world.get_components(
            Residence, Building, Active, Vacant
        ):
            # Return early if the random-roll is not sufficient
            if rng.random() > self.chance_spawn:
                return

            archetype = character_library.choose_random(rng)

            # There are no archetypes available to spawn
            if archetype is None:
                return

            # Track all the characters generated
            generated_characters: List[GameObject] = []

            # Create a new entity using the archetype
            character = archetype.spawn(self.world)
            generated_characters.append(character)

            character_config = character.get_component(GameCharacter).config

            set_life_stage(character, LifeStage.YoungAdult)


            set_residence(self.world, character, residence.gameobject, True)
            settlement.increment_population()

            spouse: Optional[GameObject] = None
            # Potentially generate a spouse for this entity
            if rng.random() < character_config.spawning.chance_spawn_with_spouse:
                # Create another character
                spouse = archetype.spawn(self.world)
                set_life_stage(spouse, LifeStage.YoungAdult)
                generated_characters.append(spouse)

                # Match the last names since they are supposed to be married
                spouse.get_component(GameCharacter).last_name = character.get_component(
                    GameCharacter
                ).last_name

                # Move them into the home with the first character
                set_residence(self.world, spouse, residence.gameobject, True)

                # Configure relationship from character to spouse
                add_relationship(self.world, character, spouse)
                get_relationship(self.world, character, spouse).add_tags(RelationshipTag.SignificantOther)
                get_relationship(self.world, character, spouse)["Romance"] += 45
                get_relationship(self.world, character, spouse)["Friendship"] += 30

                # Configure relationship from spouse to character
                add_relationship(self.world, spouse, character)
                get_relationship(self.world, spouse, character).add_tags(RelationshipTag.SignificantOther)
                get_relationship(self.world, spouse, character)["Romance"] += 45
                get_relationship(self.world, spouse, character)["Friendship"] += 30

            # Note: Characters can spawn as single parents with kids
            num_kids = rng.randint(0, character_config.spawning.max_children_at_spawn)
            children: List[GameObject] = []
            for _ in range(num_kids):
                child = archetype.spawn(self.world)
                set_life_stage(child, LifeStage.Child)
                generated_characters.append(child)

                # Match the last names since they are supposed to be married
                child.get_component(GameCharacter).last_name = character.get_component(
                    GameCharacter
                ).last_name

                # Move them into the home with the first character
                set_residence(self.world, child, residence.gameobject)
                settlement.increment_population()

                children.append(child)

                # Relationship of child to character
                child.get_component(RelationshipManager).get(character.id).add_tags("Parent")
                child.get_component(RelationshipManager).get(character.id).add_tags("Family")
                child.get_component(RelationshipManager).get(
                    character.id
                ).friendship.increase(20)

                # Relationship of character to child
                character.get_component(RelationshipManager).get(child.id).add_tags("Child")
                character.get_component(RelationshipManager).get(child.id).add_tags("Family")
                character.get_component(RelationshipManager).get(
                    child.id
                ).friendship.increase(20)

                if spouse:
                    # Relationship of child to spouse
                    child.get_component(RelationshipManager).get(spouse.id).add_tags("Parent")
                    child.get_component(RelationshipManager).get(spouse.id).add_tags("Family")
                    child.get_component(RelationshipManager).get(
                        spouse.id
                    ).friendship.increase(20)

                    # Relationship of spouse to child
                    spouse.get_component(RelationshipManager).get(child.id).add_tags("Child")
                    spouse.get_component(RelationshipManager).get(child.id).add_tags("Family")
                    spouse.get_component(RelationshipManager).get(
                        child.id
                    ).friendship.increase(20)

                for sibling in children:
                    # Relationship of child to sibling
                    child.get_component(RelationshipManager).get(sibling.id).add_tags(
                        "Sibling"
                    )
                    child.get_component(RelationshipManager).get(sibling.id).add_tags(
                        "Family"
                    )
                    child.get_component(RelationshipManager).get(
                        sibling.id
                    ).friendship.increase(20)

                    # Relationship of sibling to child
                    sibling.get_component(RelationshipManager).get(child.id).add_tags(
                        "Sibling"
                    )
                    sibling.get_component(RelationshipManager).get(child.id).add_tags(
                        "Family"
                    )
                    sibling.get_component(RelationshipManager).get(
                        child.id
                    ).friendship.increase(20)

            # Record a life event
            event_logger.record_event(
                MoveIntoTownEvent(date, residence.gameobject, *generated_characters)
            )


class BusinessUpdateSystem(System):
    def run(self, *args: Any, **kwargs: Any) -> None:
        time_increment = float(self.elapsed_time.total_days) / DAYS_PER_YEAR
        for _, (business, _) in self.world.get_components(
            Business, OpenForBusiness
        ):
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
        event_log = self.world.get_resource(EventLog)

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
                            EventRole("Character", character.gameobject.id),
                        ],
                    ),
                )

            elif character.life_stage == LifeStage.YoungAdult:
                event_log.record_event(
                    Event(
                        name="BecomeYoungAdult",
                        timestamp=current_date.to_iso_str(),
                        roles=[
                            EventRole("Character", character.gameobject.id),
                        ],
                    ),
                )

            elif character.life_stage == LifeStage.Adult:
                event_log.record_event(
                    Event(
                        name="BecomeAdult",
                        timestamp=current_date.to_iso_str(),
                        roles=[
                            EventRole("Character", character.gameobject.id),
                        ],
                    ),
                )

            elif character.life_stage == LifeStage.Senior:
                event_log.record_event(
                    Event(
                        name="BecomeSenior",
                        timestamp=current_date.to_iso_str(),
                        roles=[
                            EventRole("Character", character.gameobject.id),
                        ],
                    ),
                )


class EventSystem(ISystem):
    def process(self, *args: Any, **kwargs: Any) -> None:
        event_log = self.world.get_resource(EventLog)
        event_log.process_event_queue(self.world)
