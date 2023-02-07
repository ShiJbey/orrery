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
from orrery.components.relationship import Relationship
from orrery.components.residence import Residence, Resident, Vacant
from orrery.components.shared import Active
from orrery.content_management import LifeEventLibrary
from orrery.core.ecs import GameObject, World
from orrery.core.ecs.query import QB
from orrery.core.event import EventHandler
from orrery.core.life_event import LifeEvent, LifeEventConfig, LifeEventInstance
from orrery.core.time import SimDateTime
from orrery.events import DeathEvent
from orrery.orrery import Orrery, PluginInfo
from orrery.utils.common import depart_town, end_job, set_residence, shutdown_business
from orrery.utils.query import (
    are_related,
    is_single,
    life_stage_ge,
    with_components,
    with_relationship,
    with_statuses,
)
from orrery.utils.relationships import (
    add_relationship_status,
    get_relationship_status,
    get_relationships_with_statuses,
    remove_relationship_status,
)
from orrery.utils.statuses import add_status, remove_status


class StartDatingLifeEvent(LifeEvent):
    def __init__(self) -> None:
        super().__init__(
            name="StartDating",
            initiator_role="Initiator",
            role_query=QB.query(
                ("Initiator", "Other"),
                QB.with_((GameCharacter, Active), "Initiator"),
                QB.filter_(is_single, "Initiator"),
                with_relationship("Initiator", "Other", "?relationship_a"),
                QB.with_(Active, "Other"),
                QB.filter_(is_single, "Other"),
                QB.filter_(
                    lambda g: g.get_component(Relationship)["Romance"]
                    >= g.world.get_resource(LifeEventConfig).get(
                        "dating_romance_threshold", 0.7
                    ),
                    "?relationship_a",
                ),
                with_relationship("Other", "Initiator", "?relationship_b"),
                QB.filter_(
                    lambda g: g.get_component(Relationship)["Romance"]
                    >= g.world.get_resource(LifeEventConfig).get(
                        "dating_romance_threshold", 0.7
                    ),
                    "?relationship_b",
                ),
                QB.not_(
                    QB.filter_(
                        lambda a, b: a == b,
                        ("Initiator", "Other"),
                    )
                ),
                QB.not_(
                    QB.filter_(
                        are_related,
                        ("Initiator", "Other"),
                    )
                ),
                QB.not_(
                    QB.or_(
                        QB.with_(Dating, "?relationship_a"),
                        QB.with_(Married, "?relationship_a"),
                        QB.with_(ChildOf, "?relationship_a"),
                        QB.with_(ParentOf, "?relationship_a"),
                        QB.with_(SiblingOf, "?relationship_a"),
                    )
                ),
                QB.not_(
                    QB.or_(
                        QB.with_(Dating, "?relationship_b"),
                        QB.with_(Married, "?relationship_b"),
                        QB.with_(ChildOf, "?relationship_b"),
                        QB.with_(ParentOf, "?relationship_b"),
                        QB.with_(SiblingOf, "?relationship_b"),
                    )
                ),
            ),
        )

    def get_priority(self, event: LifeEventInstance) -> float:
        return 1

    def execute(self, event: LifeEventInstance) -> None:
        initiator = event["Initiator"]
        other = event["Other"]

        current_date = event.world.get_resource(SimDateTime)
        add_relationship_status(initiator, other, Dating(str(current_date)))
        add_relationship_status(other, initiator, Dating(str(current_date)))


class DatingBreakUp(LifeEvent):
    def __init__(self) -> None:
        super().__init__(
            name="DatingBreakup",
            initiator_role="Initiator",
            role_query=QB.query(
                ("Initiator", "Other"),
                with_components("Initiator", (GameCharacter, Active)),
                with_relationship("Initiator", "Other", "?relationship"),
                with_statuses("?relationship", Dating),
                with_components("Other", (GameCharacter, Active)),
                QB.filter_(
                    lambda rel: rel.get_component(Relationship)[
                        "Romance"
                    ].normalized_value()
                    <= rel.world.get_resource(LifeEventConfig).get(
                        "dating_breakup_thresh", 0.4
                    ),
                    "?relationship",
                ),
            ),
        )

    def get_priority(self, event: LifeEventInstance) -> float:
        return 1

    def execute(self, event: LifeEventInstance) -> None:
        initiator = event["Initiator"]
        other = event["Other"]

        remove_relationship_status(initiator, other, Dating)
        remove_relationship_status(other, initiator, Dating)


class DivorceLifeEvent(LifeEvent):
    def __init__(self):
        super().__init__(
            name="Divorce",
            initiator_role="Initiator",
            role_query=QB.query(
                ("Initiator", "Other"),
                QB.with_((GameCharacter, Active), "Initiator"),
                with_relationship("Initiator", "Other", "?relationship"),
                QB.with_(Married, "?relationship"),
                QB.filter_(
                    lambda rel: rel.get_component(Relationship)["Romance"]
                    <= rel.world.get_resource(LifeEventConfig).get(
                        "divorce_romance_thresh", 0.4
                    ),
                    "?relationship",
                ),
            ),
        )

    def get_priority(self, event: LifeEventInstance) -> float:
        return 0.8

    def execute(self, event: LifeEventInstance):
        initiator = event["Initiator"]
        ex_spouse = event["Other"]

        remove_relationship_status(initiator, ex_spouse, Married)
        remove_relationship_status(ex_spouse, initiator, Married)


class MarriageLifeEvent(LifeEvent):
    def __init__(self) -> None:
        super().__init__(
            name="GetMarried",
            initiator_role="Initiator",
            role_query=QB.query(
                ("Initiator", "Other"),
                QB.with_((GameCharacter, Active), "Initiator"),
                with_relationship("Initiator", "Other", "?relationship_a", Dating),
                with_relationship("Initiator", "Other", "?relationship_b", Dating),
                QB.not_(
                    QB.filter_(
                        lambda initiator, other: initiator == other,
                        ("Initiator", "Other"),
                    )
                ),
                QB.filter_(
                    lambda initiator, other: get_relationship_status(
                        initiator, other, Dating
                    ).years
                    > 36,
                    ("Initiator", "Other"),
                ),
                QB.filter_(
                    lambda rel: rel.get_component(Relationship)[
                        "Romance"
                    ].normalized_value()
                    >= rel.world.get_resource(LifeEventConfig).get(
                        "marriage_romance_thresh", 0.4
                    ),
                    "?relationship_a",
                ),
                QB.filter_(
                    lambda rel: rel.get_component(Relationship)[
                        "Romance"
                    ].normalized_value()
                    >= rel.world.get_resource(LifeEventConfig).get(
                        "marriage_romance_thresh", 0.4
                    ),
                    "?relationship_b",
                ),
            ),
        )

    def get_priority(self, event: LifeEventInstance) -> float:
        return 0.8

    def execute(self, event: LifeEventInstance) -> None:
        current_date = str(event.world.get_resource(SimDateTime))
        initiator = event["Initiator"]
        other = event["Other"]

        remove_relationship_status(initiator, other, Dating)
        remove_relationship_status(other, initiator, Dating)
        add_relationship_status(initiator, other, Married(current_date))
        add_relationship_status(other, initiator, Married(current_date))


class GetPregnantLifeEvent(LifeEvent):
    """Defines an event where two characters stop dating"""

    def __init__(self) -> None:
        super().__init__(
            name="GotPregnant",
            initiator_role="PregnantOne",
            role_query=QB.query(
                ("PregnantOne", "Other"),
                QB.with_((GameCharacter, Active, CanGetPregnant), "PregnantOne"),
                QB.not_(QB.with_(Pregnant, "PregnantOne")),
                with_relationship("PregnantOne", "Other", "?relationship"),
                QB.with_((GameCharacter, Active), "Other"),
                QB.or_(
                    QB.with_(Dating, "?relationship"),
                    QB.with_(Married, "?relationship"),
                ),
            ),
        )

    def execute(self, event: LifeEventInstance):
        current_date = event.world.get_resource(SimDateTime)
        due_date = current_date.copy()
        due_date.increment(months=9)

        add_status(
            event["PregnantOne"],
            Pregnant(
                created=str(current_date),
                partner_id=event["Other"].uid,
                due_date=due_date,
            ),
        )

    def get_priority(self, event: LifeEventInstance):
        gameobject = event.roles["PregnantOne"]
        children = get_relationships_with_statuses(gameobject, ParentOf)
        if len(children) >= 5:
            return 0.0
        else:
            return 4.0 - len(children) / 8.0


class RetireLifeEvent(LifeEvent):
    def __init__(self) -> None:
        super().__init__(
            name="Retire",
            initiator_role="Retiree",
            role_query=QB.query(
                "Retiree",
                QB.with_((GameCharacter, Active, Occupation), "Retiree"),
                QB.filter_(life_stage_ge(LifeStage.Senior), "Retiree"),
                QB.not_(QB.with_(Retired, "Retiree")),
            ),
        )

    def get_priority(self, event: LifeEventInstance) -> float:
        return event.world.get_resource(LifeEventConfig).get("retirement_prb", 0.4)

    def execute(self, event: LifeEventInstance) -> None:
        date = event.world.get_resource(SimDateTime)
        retiree = event["Retiree"]
        add_status(retiree, Retired(date.to_iso_str()))
        end_job(retiree, event.get_name())


class FindOwnPlaceLifeEvent(LifeEvent):
    def __init__(self) -> None:
        super().__init__(
            name="FindOwnPlace",
            initiator_role="Character",
            role_query=QB.query(
                "Character", QB.from_(self.bind_potential_mover, "Character")
            ),
        )

    def get_priority(self, event: LifeEventInstance) -> float:
        return 0.7

    @staticmethod
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

    @staticmethod
    def find_vacant_residences(world: World) -> List[GameObject]:
        """Try to find a vacant residence to move into"""
        return list(
            map(
                lambda pair: world.get_gameobject(pair[0]),
                world.get_components((Residence, Vacant)),
            )
        )

    @staticmethod
    def choose_random_vacant_residence(world: World) -> Optional[GameObject]:
        """Randomly chooses a vacant residence to move into"""
        vacancies = FindOwnPlaceLifeEvent.find_vacant_residences(world)
        if vacancies:
            return world.get_resource(random.Random).choice(vacancies)
        return None

    def execute(self, event: LifeEventInstance):
        # Try to find somewhere to live
        character = event["Character"]
        vacant_residence = FindOwnPlaceLifeEvent.choose_random_vacant_residence(
            event.world
        )
        if vacant_residence:
            # Move into house with any dependent children
            set_residence(event.world, character, vacant_residence)

        # Depart if no housing could be found
        else:
            depart_town(event.world, character, event.get_name())


class DieOfOldAgeLifeEvent(LifeEvent):
    def __init__(self) -> None:
        super().__init__(
            name="DieOfOldAge",
            initiator_role="Deceased",
            role_query=QB.query(
                "Deceased",
                QB.with_((GameCharacter, Active), "Deceased"),
                QB.filter_(
                    lambda gameobject: gameobject.get_component(GameCharacter).age
                    >= gameobject.get_component(GameCharacter).config.aging.lifespan,
                    "Deceased",
                ),
            ),
        )

    def get_priority(self, event: LifeEventInstance) -> float:
        return 0.8

    def execute(self, event: LifeEventInstance) -> None:
        current_date = event.world.get_resource(SimDateTime)
        deceased = event["Deceased"]
        add_status(deceased, Deceased(current_date.to_iso_str()))
        remove_status(deceased, Active)
        event.world.get_resource(EventHandler).emit(
            DeathEvent(event.world.get_resource(SimDateTime), deceased)
        )


class GoOutOfBusinessLifeEvent(LifeEvent):
    def __init__(self) -> None:
        super().__init__(
            name="GoOutOfBusiness",
            initiator_role="Business",
            role_query=QB.query(
                "Business", QB.with_((Business, OpenForBusiness, Active), "Business")
            ),
        )

    def execute(self, event: LifeEventInstance):
        shutdown_business(event["Business"])

    def get_priority(self, event: LifeEventInstance) -> float:
        business = event.roles["Business"].get_component(Business)
        if business.years_in_business < 5:
            return 0.0
        elif business.years_in_business < business.config.spawning.lifespan:
            return business.years_in_business / business.config.spawning.lifespan
        else:
            return 0.7


plugin_info: PluginInfo = {
    "name": "default life events plugin",
    "plugin_id": "default.life-events",
    "version": "0.1.0",
}


def setup(sim: Orrery):
    life_event_library = sim.world.get_resource(LifeEventLibrary)

    life_event_library.add(MarriageLifeEvent())
    life_event_library.add(StartDatingLifeEvent())
    life_event_library.add(DatingBreakUp())
    life_event_library.add(DivorceLifeEvent())
    life_event_library.add(GetPregnantLifeEvent())
    life_event_library.add(RetireLifeEvent())
    life_event_library.add(FindOwnPlaceLifeEvent())
    life_event_library.add(DieOfOldAgeLifeEvent())
    life_event_library.add(GoOutOfBusinessLifeEvent())
