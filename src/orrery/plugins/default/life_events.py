from __future__ import annotations

import random
from typing import Any, List, Optional, Tuple, cast

import orrery.events
from orrery.components.business import Business, Occupation, OpenForBusiness
from orrery.components.character import (
    CanGetPregnant,
    Deceased,
    GameCharacter,
    LifeStage,
    Pregnant,
    Retired,
)
from orrery.components.residence import Residence, Resident, Vacant
from orrery.components.shared import Active
from orrery.core.ecs import GameObject, World
from orrery.core.event import Event, EventLog, EventRoleType, RoleList
from orrery.core.life_event import (
    ILifeEvent,
    LifeEvent,
    LifeEventInstance,
    LifeEventLibrary,
)
from orrery.core.query import QueryBuilder, not_, or_
from orrery.core.relationship import RelationshipManager, RelationshipTag
from orrery.core.time import SimDateTime
from orrery.orrery import Plugin
from orrery.utils.common import (
    add_status,
    depart_town,
    end_job,
    has_status,
    set_residence,
    shutdown_business,
)
from orrery.utils.query import (
    friendship_gte,
    friendship_lte,
    from_pattern,
    from_roles,
    get_friendships_gte,
    get_friendships_lte,
    get_relationships_with_tags,
    get_romances_gte,
    has_component,
    is_single,
    relationship_has_tags,
    romance_gte,
    romance_lte,
)


def become_friends_event(
    threshold: float = 0.7, probability: float = 1.0
) -> ILifeEvent:
    """Defines an event where two characters become friends"""

    def effect(world: World, event: Event):
        world.get_gameobject(event["Initiator"]).get_component(RelationshipManager).get(
            event["Other"]
        ).add_tags(RelationshipTag.Friend)

        world.get_gameobject(event["Other"]).get_component(RelationshipManager).get(
            event["Initiator"]
        ).add_tags(RelationshipTag.Friend)

    return LifeEvent(
        name="BecomeFriends",
        bind_fn=from_pattern(
            QueryBuilder("Initiator", "Other")
            .with_((GameCharacter, Active), "Initiator")
            .get_(get_friendships_gte(threshold), "Initiator", "Other")
            .filter_(has_component(Active), "Other")
            .filter_(friendship_gte(threshold), "Other", "Initiator")
            .filter_(
                not_(relationship_has_tags(RelationshipTag.Friend)),
                "Initiator",
                "Other",
            )
            .build()
        ),
        effect=effect,
        probability=probability,
    )


def become_enemies_event(
    threshold: float = 0.3, probability: float = 1.0
) -> ILifeEvent:
    """Defines an event where two characters become friends"""

    def effect(world: World, event: Event):
        world.get_gameobject(event["Initiator"]).get_component(RelationshipManager).get(
            event["Other"]
        ).add_tags(RelationshipTag.Enemy)

        world.get_gameobject(event["Other"]).get_component(RelationshipManager).get(
            event["Initiator"]
        ).add_tags(RelationshipTag.Enemy)

    return LifeEvent(
        name="BecomeEnemies",
        bind_fn=from_pattern(
            QueryBuilder("Initiator", "Other")
            .with_((GameCharacter, Active), "Initiator")
            .get_(get_friendships_lte(threshold), "Initiator", "Other")
            .with_((Active,), "Other")
            .filter_(friendship_lte(threshold), "Other", "Initiator")
            .filter_(
                not_(relationship_has_tags(RelationshipTag.Enemy)), "Initiator", "Other"
            )
            .build()
        ),
        effect=effect,
        probability=probability,
    )


def start_dating_event(threshold: float = 0.7, probability: float = 1.0) -> ILifeEvent:
    """Defines an event where two characters become friends"""

    def effect(world: World, event: Event):
        world.get_gameobject(event["Initiator"]).get_component(RelationshipManager).get(
            event["Other"]
        ).add_tags(RelationshipTag.Dating | RelationshipTag.SignificantOther)

        world.get_gameobject(event["Other"]).get_component(RelationshipManager).get(
            event["Initiator"]
        ).add_tags(RelationshipTag.Dating | RelationshipTag.SignificantOther)

    return LifeEvent(
        name="StartDating",
        bind_fn=from_pattern(
            QueryBuilder("Initiator", "Other")
            .with_((GameCharacter, Active), "Initiator")
            .get_(get_romances_gte(threshold), "Initiator", "Other")
            .filter_(has_component(Active), "Other")
            .filter_(romance_gte(threshold), "Other", "Initiator")
            .filter_(
                not_(
                    relationship_has_tags(
                        RelationshipTag.SignificantOther | RelationshipTag.Family
                    )
                ),
                "Initiator",
                "Other",
            )
            .filter_(
                not_(
                    relationship_has_tags(
                        RelationshipTag.SignificantOther | RelationshipTag.Family
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
        world.get_gameobject(event["Initiator"]).get_component(RelationshipManager).get(
            event["Other"]
        ).remove_tags(RelationshipTag.Dating | RelationshipTag.SignificantOther)

        world.get_gameobject(event["Other"]).get_component(RelationshipManager).get(
            event["Initiator"]
        ).remove_tags(RelationshipTag.Dating | RelationshipTag.SignificantOther)

    return LifeEvent(
        name="DatingBreakUp",
        bind_fn=from_pattern(
            QueryBuilder("Initiator", "Other")
            .with_((GameCharacter, Active), "Initiator")
            .get_(
                get_relationships_with_tags(RelationshipTag.Dating),
                "Initiator",
                "Other",
            )
            .filter_(romance_lte(threshold), "Initiator", "Other")
            .build()
        ),
        effect=effect,
        probability=probability,
    )


def divorce_event(threshold: float = 0.4, probability: float = 1.0) -> ILifeEvent:
    """Defines an event where two characters become friends"""

    def effect(world: World, event: Event):
        world.get_gameobject(event["Initiator"]).get_component(RelationshipManager).get(
            event["Other"]
        ).remove_tags(RelationshipTag.Spouse | RelationshipTag.SignificantOther)

        world.get_gameobject(event["Other"]).get_component(RelationshipManager).get(
            event["Initiator"]
        ).remove_tags(RelationshipTag.Spouse | RelationshipTag.SignificantOther)

    return LifeEvent(
        name="Divorce",
        bind_fn=from_pattern(
            QueryBuilder("Initiator", "Other")
            .with_((GameCharacter, Active), "Initiator")
            .get_(
                get_relationships_with_tags(RelationshipTag.Spouse),
                "Initiator",
                "Other",
            )
            .filter_(romance_lte(threshold), "Initiator", "Other")
            .build()
        ),
        effect=effect,
        probability=probability,
    )


def marriage_event(threshold: float = 0.7, probability: float = 1.0) -> ILifeEvent:
    """Defines an event where two characters become friends"""

    def effect(world: World, event: Event):
        world.get_gameobject(event["Initiator"]).get_component(RelationshipManager).get(
            event["Other"]
        ).add_tags(RelationshipTag.Spouse | RelationshipTag.SignificantOther)

        world.get_gameobject(event["Initiator"]).get_component(RelationshipManager).get(
            event["Other"]
        ).remove_tags(RelationshipTag.Dating)

        world.get_gameobject(event["Other"]).get_component(RelationshipManager).get(
            event["Initiator"]
        ).add_tags(RelationshipTag.Spouse | RelationshipTag.SignificantOther)

        world.get_gameobject(event["Other"]).get_component(RelationshipManager).get(
            event["Initiator"]
        ).remove_tags(RelationshipTag.Dating)

    return LifeEvent(
        name="GetMarried",
        bind_fn=from_pattern(
            QueryBuilder("Initiator", "Other")
            .with_((GameCharacter, Active), "Initiator")
            .get_(
                get_relationships_with_tags(RelationshipTag.Dating),
                "Initiator",
                "Other",
            )
            .filter_(romance_gte(threshold), "Initiator", "Other")
            .filter_(romance_gte(threshold), "Other", "Initiator")
            .build()
        ),
        effect=effect,
        probability=probability,
    )


def pregnancy_event() -> ILifeEvent:
    """Defines an event where two characters stop dating"""

    def execute(world: World, event: Event):
        due_date = SimDateTime.from_iso_str(
            world.get_resource(SimDateTime).to_iso_str()
        )
        due_date.increment(months=9)

        add_status(
            world,
            world.get_gameobject(event["PregnantOne"]),
            Pregnant(
                partner_id=event["Other"],
                due_date=due_date,
            ),
        )

    def prob_fn(world: World, event: LifeEventInstance):
        gameobject = world.get_gameobject(event.roles["PregnantOne"])
        children = gameobject.get_component(RelationshipManager).get_all_with_tags(
            RelationshipTag.Child
        )
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
                get_relationships_with_tags(RelationshipTag.Spouse),
                "PregnantOne",
                "Other",
            )
            .filter_(has_component(Active), "Other")
            .filter_(
                or_(
                    relationship_has_tags(RelationshipTag.Dating),
                    relationship_has_tags(RelationshipTag.Married),
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
            if not candidate.has_component(Retired) and candidate.has_component(
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
            GameCharacter, Occupation, Active
        ):
            character = cast(GameCharacter, character)

            if character.life_stage < LifeStage.Senior:
                continue

            gameobject = world.get_gameobject(gid)
            if not gameobject.has_component(Retired):
                eligible_characters.append(gameobject)
        if eligible_characters:
            return world.get_resource(random.Random).choice(eligible_characters)
        return None

    def execute(world: World, event: Event):
        retiree = world.get_gameobject(event["Retiree"])
        retiree.add_component(Retired())
        end_job(world, retiree, event.name)

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
            GameCharacter, Occupation, Resident, Active
        ):
            character = cast(GameCharacter, character)
            resident = cast(Resident, resident)

            if character.life_stage < LifeStage.YoungAdult:
                continue

            residence = world.get_gameobject(resident.residence).get_component(
                Residence
            )
            if gid not in residence.owners:
                eligible.append((gid,))

        return eligible

    def find_vacant_residences(world: World) -> List[Residence]:
        """Try to find a vacant residence to move into"""
        return list(
            map(
                lambda pair: cast(Residence, pair[1][0]),
                world.get_components(Residence, Vacant),
            )
        )

    def choose_random_vacant_residence(world: World) -> Optional[Residence]:
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
            set_residence(world, character, vacant_residence.gameobject)

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
        deceased = world.get_gameobject(event["Deceased"])
        deceased.add_component(Deceased())
        deceased.remove_component(Active)
        world.get_resource(EventLog).record_event(
            orrery.events.DeathEvent(world.get_resource(SimDateTime), deceased)
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
        shutdown_business(world, business)

    def probability_fn(world: World, event: LifeEventInstance) -> float:
        business = world.get_gameobject(event.roles["Business"]).get_component(Business)
        if business.years_in_business < 5:
            return 0
        elif business.years_in_business < business.config.spawning.lifespan:
            return business.years_in_business / business.config.spawning.lifespan
        else:
            return 0.8

    return LifeEvent(
        name="GoOutOfBusiness",
        bind_fn=from_pattern(
            QueryBuilder("Business").with_((Business, OpenForBusiness, Active)).build()
        ),
        effect=effect,
        probability=probability_fn,
    )


class DefaultLifeEventPlugin(Plugin):
    def setup(self, world: World, **kwargs: Any) -> None:
        life_event_library = world.get_resource(LifeEventLibrary)

        life_event_library.add(marriage_event())
        # LifeEvents.add(become_friends_event())
        # LifeEvents.add(become_enemies_event())
        life_event_library.add(start_dating_event())
        life_event_library.add(stop_dating_event())
        life_event_library.add(divorce_event())
        life_event_library.add(pregnancy_event())
        life_event_library.add(retire_event())
        life_event_library.add(find_own_place_event())
        life_event_library.add(die_of_old_age())
        life_event_library.add(go_out_of_business_event())


def get_plugin() -> Plugin:
    return DefaultLifeEventPlugin()
