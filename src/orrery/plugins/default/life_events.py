from __future__ import annotations

import random
from typing import Any, List, Optional, Tuple

from orrery.components.business import Business, Occupation, OpenForBusiness
from orrery.components.character import (
    CanGetPregnant,
    ChildOf,
    Dating,
    Deceased,
    GameCharacter,
    LifeStage,
    Married,
    ParentOf,
    Pregnant,
    Retired,
    SiblingOf,
)
from orrery.components.residence import Residence, Resident, Vacant
from orrery.components.shared import Active
from orrery.content_management import LifeEventLibrary
from orrery.core.ecs import GameObject, World
from orrery.core.ecs.query import QueryBuilder, not_, or_
from orrery.core.event import Event, EventHandler, EventRoleType, RoleList
from orrery.core.life_event import ILifeEvent, LifeEvent, LifeEventInstance
from orrery.core.time import SimDateTime
from orrery.events import DeathEvent
from orrery.orrery import Orrery, PluginInfo
from orrery.utils.common import depart_town, end_job, set_residence, shutdown_business
from orrery.utils.query import (
    filter_relationship_has_statuses,
    filter_relationship_stat_gte,
    filter_relationship_stat_lte,
    find_relationships_with_statuses,
    find_with_relationship_stat_gte,
    from_pattern,
    from_roles,
    has_component_filter,
    is_single,
)
from orrery.utils.relationships import (
    add_relationship_status,
    get_relationship_status,
    get_relationships_with_statuses,
    remove_relationship_status,
)
from orrery.utils.statuses import add_status, has_status, remove_status


def start_dating_event(threshold: float = 0.7, probability: float = 1.0) -> ILifeEvent:
    """Defines an event where two characters become friends"""

    def effect(world: World, event: Event):
        current_date = world.get_resource(SimDateTime).to_iso_str()
        initiator = world.get_gameobject(event["Initiator"])
        other = world.get_gameobject(event["Other"])

        add_relationship_status(initiator, other, Dating(current_date))
        add_relationship_status(other, initiator, Dating(current_date))

    return LifeEvent(
        name="StartDating",
        bind_fn=from_pattern(
            QueryBuilder("Initiator", "Other")
            .with_((GameCharacter, Active), "Initiator")
            .get_(
                find_with_relationship_stat_gte("Romance", threshold),
                "Initiator",
                "Other",
            )
            .filter_(has_component_filter(Active), "Other")
            .filter_(
                filter_relationship_stat_gte("Romance", threshold), "Other", "Initiator"
            )
            .filter_(
                not_(lambda world, *gameobjects: gameobjects[0] == gameobjects[1]),
                "Initiator",
                "Other",
            )
            .filter_(
                not_(
                    or_(
                        filter_relationship_has_statuses(Dating),
                        filter_relationship_has_statuses(Married),
                        filter_relationship_has_statuses(ChildOf),
                        filter_relationship_has_statuses(ParentOf),
                        filter_relationship_has_statuses(SiblingOf),
                    )
                ),
                "Initiator",
                "Other",
            )
            .filter_(
                not_(
                    or_(
                        filter_relationship_has_statuses(Dating),
                        filter_relationship_has_statuses(Married),
                        filter_relationship_has_statuses(ChildOf),
                        filter_relationship_has_statuses(ParentOf),
                        filter_relationship_has_statuses(SiblingOf),
                    )
                ),
                "Other",
                "Initiator",
            )
            .filter_(is_single, "Initiator")
            .filter_(is_single, "Other")
            .build()
        ),
        effect=effect,
        probability=probability,
    )


def stop_dating_event(threshold: float = 0.4, probability: float = 1.0) -> ILifeEvent:
    """Defines an event where two characters become friends"""

    def effect(world: World, event: Event):
        initiator = world.get_gameobject(event["Initiator"])
        other = world.get_gameobject(event["Other"])

        remove_relationship_status(initiator, other, Dating)
        remove_relationship_status(other, initiator, Dating)

    return LifeEvent(
        name="DatingBreakUp",
        bind_fn=from_pattern(
            QueryBuilder("Initiator", "Other")
            .with_((GameCharacter, Active), "Initiator")
            .get_(
                find_relationships_with_statuses(Dating),
                "Initiator",
                "Other",
            )
            .filter_(
                filter_relationship_stat_lte("Romance", threshold), "Initiator", "Other"
            )
            .build()
        ),
        effect=effect,
        probability=probability,
    )


def divorce_event(threshold: float = 0.4, probability: float = 1.0) -> ILifeEvent:
    """Defines an event where two characters become friends"""

    def effect(world: World, event: Event):
        initiator = world.get_gameobject(event["Initiator"])
        ex_spouse = world.get_gameobject(event["Other"])

        remove_relationship_status(initiator, ex_spouse, Married)
        remove_relationship_status(ex_spouse, initiator, Married)

    return LifeEvent(
        name="Divorce",
        bind_fn=from_pattern(
            QueryBuilder("Initiator", "Other")
            .with_((GameCharacter, Active), "Initiator")
            .get_(
                find_relationships_with_statuses(Married),
                "Initiator",
                "Other",
            )
            .filter_(
                filter_relationship_stat_lte("Romance", threshold), "Initiator", "Other"
            )
            .build()
        ),
        effect=effect,
        probability=probability,
    )


def marriage_event(threshold: float = 0.7, probability: float = 1.0) -> ILifeEvent:
    """Defines an event where two characters become friends"""

    def effect(world: World, event: Event):
        current_date = world.get_resource(SimDateTime).to_iso_str()
        initiator = world.get_gameobject(event["Initiator"])
        other = world.get_gameobject(event["Other"])

        remove_relationship_status(initiator, other, Dating)
        remove_relationship_status(other, initiator, Dating)
        add_relationship_status(initiator, other, Married(current_date))
        add_relationship_status(other, initiator, Married(current_date))

    return LifeEvent(
        name="GetMarried",
        bind_fn=from_pattern(
            QueryBuilder("Initiator", "Other")
            .with_((GameCharacter, Active), "Initiator")
            .get_(
                find_relationships_with_statuses(Dating),
                "Initiator",
                "Other",
            )
            .filter_(
                not_(lambda world, *gameobjects: gameobjects[0] == gameobjects[1]),
                "Initiator",
                "Other",
            )
            .filter_(
                lambda world, *gameobjects: get_relationship_status(
                    gameobjects[0], gameobjects[1], Dating
                ).years
                > 36,
                "Initiator",
                "Other",
            )
            .filter_(
                filter_relationship_stat_gte("Romance", threshold), "Initiator", "Other"
            )
            .filter_(
                filter_relationship_stat_gte("Romance", threshold), "Other", "Initiator"
            )
            .build()
        ),
        effect=effect,
        probability=probability,
    )


def pregnancy_event() -> ILifeEvent:
    """Defines an event where two characters stop dating"""

    def execute(world: World, event: Event):
        current_date = world.get_resource(SimDateTime)
        due_date = SimDateTime.from_iso_str(
            world.get_resource(SimDateTime).to_iso_str()
        )
        due_date.increment(months=9)

        add_status(
            world.get_gameobject(event["PregnantOne"]),
            Pregnant(
                created=current_date.to_iso_str(),
                partner_id=event["Other"],
                due_date=due_date,
            ),
        )

    def prob_fn(world: World, event: LifeEventInstance):
        gameobject = world.get_gameobject(event.roles["PregnantOne"])
        children = get_relationships_with_statuses(gameobject, ParentOf)
        if len(children) >= 5:
            return 0.0
        else:
            return 4.0 - len(children) / 8.0

    return LifeEvent(
        name="GotPregnant",
        bind_fn=from_pattern(
            QueryBuilder("PregnantOne", "Other")
            .with_((GameCharacter, Active, CanGetPregnant), "PregnantOne")
            .filter_(
                not_(lambda world, *gameobjects: has_status(gameobjects[0], Pregnant)),
                "PregnantOne",
            )
            .get_(
                find_relationships_with_statuses(Married),
                "PregnantOne",
                "Other",
            )
            .filter_(has_component_filter(Active), "Other")
            .filter_(
                or_(
                    filter_relationship_has_statuses(Dating),
                    filter_relationship_has_statuses(Married),
                ),
                "PregnantOne",
                "Other",
            )
            .build()
        ),
        effect=execute,
        probability=prob_fn,
    )


def retire_event(probability: float = 0.4) -> ILifeEvent:
    """
    Event for characters retiring from working after reaching elder status

    Parameters
    ----------
    probability: float
        Probability that an entity will retire from their job
        when they are an elder

    Returns
    -------
    LifeEvent
        LifeEventType instance with all configuration defined
    """

    def bind_retiree(
        world: World, roles: RoleList, candidate: Optional[GameObject] = None
    ):

        if candidate:
            if not candidate.has_component(Retired) and candidate.has_components(
                Occupation, Active
            ):
                if (
                    candidate.get_component(GameCharacter).life_stage
                    >= LifeStage.Senior
                ):
                    return candidate
            return None

        eligible_characters: List[GameObject] = []

        for gid, (character, _, _) in world.get_components(
            (GameCharacter, Occupation, Active)
        ):

            if character.life_stage < LifeStage.Senior:
                continue

            gameobject = world.get_gameobject(gid)
            if not gameobject.has_component(Retired):
                eligible_characters.append(gameobject)
        if eligible_characters:
            return world.get_resource(random.Random).choice(eligible_characters)
        return None

    def execute(world: World, event: Event):
        date = world.get_resource(SimDateTime)
        retiree = world.get_gameobject(event["Retiree"])
        add_status(retiree, Retired(date.to_iso_str()))
        end_job(retiree, event.name)

    return LifeEvent(
        name="Retire",
        bind_fn=from_roles(EventRoleType(name="Retiree", binder_fn=bind_retiree)),
        effect=execute,
        probability=probability,
    )


def find_own_place_event(probability: float = 0.1) -> ILifeEvent:
    def bind_potential_mover(world: World) -> List[Tuple[Any, ...]]:
        eligible: List[Tuple[Any, ...]] = []

        for gid, (character, _, resident, _) in world.get_components(
            (GameCharacter, Occupation, Resident, Active)
        ):

            if character.life_stage < LifeStage.YoungAdult:
                continue

            residence = world.get_gameobject(resident.residence).get_component(
                Residence
            )
            if gid not in residence.owners:
                eligible.append((gid,))

        return eligible

    def find_vacant_residences(world: World) -> List[GameObject]:
        """Try to find a vacant residence to move into"""
        return list(
            map(
                lambda pair: world.get_gameobject(pair[0]),
                world.get_components((Residence, Vacant)),
            )
        )

    def choose_random_vacant_residence(world: World) -> Optional[GameObject]:
        """Randomly chooses a vacant residence to move into"""
        vacancies = find_vacant_residences(world)
        if vacancies:
            return world.get_resource(random.Random).choice(vacancies)
        return None

    def execute(world: World, event: Event):
        # Try to find somewhere to live
        character = world.get_gameobject(event["Character"])
        vacant_residence = choose_random_vacant_residence(world)
        if vacant_residence:
            # Move into house with any dependent children
            set_residence(world, character, vacant_residence)

        # Depart if no housing could be found
        else:
            depart_town(world, character, event.name)

    return LifeEvent(
        name="FindOwnPlace",
        probability=probability,
        bind_fn=from_pattern(
            QueryBuilder("Character").from_(bind_potential_mover).build()
        ),
        effect=execute,
    )


def die_of_old_age(probability: float = 0.8) -> ILifeEvent:
    def execute(world: World, event: Event) -> None:
        current_date = world.get_resource(SimDateTime)
        deceased = world.get_gameobject(event["Deceased"])
        add_status(deceased, Deceased(current_date.to_iso_str()))
        remove_status(deceased, Active)
        world.get_resource(EventHandler).emit(
            DeathEvent(world.get_resource(SimDateTime), deceased)
        )

    return LifeEvent(
        name="DieOfOldAge",
        probability=probability,
        bind_fn=from_pattern(
            QueryBuilder("Deceased")
            .with_((GameCharacter, Active))
            .filter_(
                lambda world, *gameobjects: gameobjects[0]
                .get_component(GameCharacter)
                .age
                >= gameobjects[0].get_component(GameCharacter).config.aging.lifespan
            )
            .build()
        ),
        effect=execute,
    )


def go_out_of_business_event() -> ILifeEvent:
    def effect(world: World, event: Event):
        business = world.get_gameobject(event["Business"])
        shutdown_business(business)

    def probability_fn(world: World, event: LifeEventInstance) -> float:
        business = world.get_gameobject(event.roles["Business"]).get_component(Business)
        if business.years_in_business < 5:
            return 0
        elif business.years_in_business < business.config.spawning.lifespan:
            return business.years_in_business / business.config.spawning.lifespan
        else:
            return 0.7

    return LifeEvent(
        name="GoOutOfBusiness",
        bind_fn=from_pattern(
            QueryBuilder("Business").with_((Business, OpenForBusiness, Active)).build()
        ),
        effect=effect,
        probability=probability_fn,
    )


plugin_info: PluginInfo = {
    "name": "default life events plugin",
    "plugin_id": "default.life-events",
    "version": "0.1.0",
}


def setup(sim: Orrery):
    life_event_library = sim.world.get_resource(LifeEventLibrary)

    life_event_library.add(marriage_event())
    life_event_library.add(start_dating_event())
    life_event_library.add(stop_dating_event())
    life_event_library.add(divorce_event())
    life_event_library.add(pregnancy_event())
    life_event_library.add(retire_event())
    life_event_library.add(find_own_place_event())
    life_event_library.add(die_of_old_age())
    life_event_library.add(go_out_of_business_event())
