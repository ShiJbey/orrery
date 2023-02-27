from __future__ import annotations

import random
from typing import Any, Dict, Generator, List, Optional, Tuple

from orrery import OrreryConfig
from orrery.components.business import (
    Business,
    BusinessOwner,
    InTheWorkforce,
    Occupation,
    OpenForBusiness,
)
from orrery.components.character import (
    AgingConfig,
    CanGetPregnant,
    ChildOf,
    Dating,
    Deceased,
    GameCharacter,
    Married,
    ParentOf,
    Pregnant,
    Retired,
    Senior,
    SiblingOf,
    YoungAdult,
)
from orrery.components.residence import Residence, Resident, Vacant
from orrery.components.shared import Active
from orrery.content_management import (
    BusinessLibrary,
    LifeEventLibrary,
    OccupationTypeLibrary,
)
from orrery.core.ecs import GameObject, World
from orrery.core.ecs.query import QB
from orrery.core.life_event import ActionableLifeEvent, LifeEventBuffer
from orrery.core.relationship import Romance
from orrery.core.roles import Role, RoleList
from orrery.core.time import SimDateTime
from orrery.orrery import Orrery, PluginInfo
from orrery.prefabs import BusinessPrefab
from orrery.utils.common import (
    clear_frequented_locations,
    depart_settlement,
    end_job,
    get_life_stage,
    remove_character_from_settlement,
    set_residence,
    shutdown_business,
)
from orrery.utils.query import (
    are_related,
    is_single,
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
from orrery.utils.statuses import add_status, clear_statuses


class StartDatingLifeEvent(ActionableLifeEvent):

    optional = True
    initiator = "Initiator"

    def get_priority(self) -> float:
        return 1

    def execute(self) -> None:
        initiator = self["Initiator"]
        other = self["Other"]

        add_relationship_status(initiator, other, Dating())
        add_relationship_status(other, initiator, Dating())

    @classmethod
    def instantiate(
        cls,
        world: World,
        bindings: Optional[RoleList] = None,
    ) -> Optional[ActionableLifeEvent]:
        query = QB.query(
            ("Initiator", "Other"),
            QB.with_((GameCharacter, Active), "Initiator"),
            QB.filter_(is_single, "Initiator"),
            with_relationship("Initiator", "Other", "?relationship_a"),
            QB.with_(Active, "Other"),
            QB.filter_(is_single, "Other"),
            QB.filter_(
                lambda g: g.get_component(Romance).get_value()
                >= g.world.get_resource(OrreryConfig).settings.get(
                    "dating_romance_threshold", 25
                ),
                "?relationship_a",
            ),
            with_relationship("Other", "Initiator", "?relationship_b"),
            QB.filter_(
                lambda g: g.get_component(Romance).get_value()
                >= g.world.get_resource(OrreryConfig).settings.get(
                    "dating_romance_threshold", 25
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
        )

        if bindings:
            results = query.execute(world, {r.name: r.gameobject.uid for r in bindings})
        else:
            results = query.execute(world)

        if results:
            chosen_result = world.get_resource(random.Random).choice(results)
            chosen_objects = [world.get_gameobject(uid) for uid in chosen_result]
            roles = dict(zip(query.get_symbols(), chosen_objects))
            return cls(world.get_resource(SimDateTime), [Role(title, gameobject) for title, gameobject in roles.items()])


class DatingBreakUp(ActionableLifeEvent):

    initiator = "Initiator"

    def get_priority(self) -> float:
        return 1

    def execute(self) -> None:
        initiator = self["Initiator"]
        other = self["Other"]

        remove_relationship_status(initiator, other, Dating)
        remove_relationship_status(other, initiator, Dating)

    @classmethod
    def instantiate(
        cls,
        world: World,
        bindings: Optional[RoleList] = None,
    ) -> Optional[ActionableLifeEvent]:
        query = QB.query(
            ("Initiator", "Other"),
            with_components("Initiator", (GameCharacter, Active)),
            with_relationship("Initiator", "Other", "?relationship"),
            with_statuses("?relationship", Dating),
            with_components("Other", (GameCharacter, Active)),
            QB.filter_(
                lambda rel: rel.get_component(Romance).get_value()
                <= rel.world.get_resource(OrreryConfig).settings.get(
                    "dating_breakup_thresh", 20
                ),
                "?relationship",
            ),
        )

        if bindings:
            results = query.execute(world, {r.name: r.gameobject.uid for r in bindings})
        else:
            results = query.execute(world)

        if results:
            chosen_result = world.get_resource(random.Random).choice(results)
            chosen_objects = [world.get_gameobject(uid) for uid in chosen_result]
            roles = dict(zip(query.get_symbols(), chosen_objects))
            return cls(world.get_resource(SimDateTime), [Role(title, gameobject) for title, gameobject in roles.items()])


class DivorceLifeEvent(ActionableLifeEvent):
    @classmethod
    def instantiate(
        cls,
        world: World,
        bindings: Optional[RoleList] = None,
    ) -> Optional[ActionableLifeEvent]:
        query = QB.query(
            ("Initiator", "Other"),
            QB.with_((GameCharacter, Active), "Initiator"),
            with_relationship("Initiator", "Other", "?relationship"),
            QB.with_(Married, "?relationship"),
            QB.filter_(
                lambda rel: rel.get_component(Romance).get_value()
                <= rel.world.get_resource(OrreryConfig).settings.get(
                    "divorce_romance_thresh", -25
                ),
                "?relationship",
            ),
        )

        if bindings:
            results = query.execute(world, {r.name: r.gameobject.uid for r in bindings})
        else:
            results = query.execute(world)

        if results:
            chosen_result = world.get_resource(random.Random).choice(results)
            chosen_objects = [world.get_gameobject(uid) for uid in chosen_result]
            roles = dict(zip(query.get_symbols(), chosen_objects))
            return cls(world.get_resource(SimDateTime), [Role(title, gameobject) for title, gameobject in roles.items()])

    def get_priority(self) -> float:
        return 0.8

    def execute(self):
        initiator = self["Initiator"]
        ex_spouse = self["Other"]

        remove_relationship_status(initiator, ex_spouse, Married)
        remove_relationship_status(ex_spouse, initiator, Married)


class MarriageLifeEvent(ActionableLifeEvent):
    @classmethod
    def instantiate(
        cls,
        world: World,
        bindings: Optional[RoleList] = None,
    ) -> Optional[ActionableLifeEvent]:
        query = QB.query(
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
                lambda rel: rel.get_component(Romance).get_value()
                >= rel.world.get_resource(OrreryConfig).settings.get(
                    "marriage_romance_thresh", 25
                ),
                "?relationship_a",
            ),
            QB.filter_(
                lambda rel: rel.get_component(Romance).get_value()
                >= rel.world.get_resource(OrreryConfig).settings.get(
                    "marriage_romance_thresh", 25
                ),
                "?relationship_b",
            ),
        )

        if bindings:
            results = query.execute(world, {r.name: r.gameobject.uid for r in bindings})
        else:
            results = query.execute(world)

        if results:
            chosen_result = world.get_resource(random.Random).choice(results)
            chosen_objects = [world.get_gameobject(uid) for uid in chosen_result]
            roles = dict(zip(query.get_symbols(), chosen_objects))
            return cls(world.get_resource(SimDateTime), [Role(title, gameobject) for title, gameobject in roles.items()])

    def get_priority(self) -> float:
        return 0.8

    def execute(self) -> None:
        initiator = self["Initiator"]
        other = self["Other"]

        remove_relationship_status(initiator, other, Dating)
        remove_relationship_status(other, initiator, Dating)
        add_relationship_status(initiator, other, Married())
        add_relationship_status(other, initiator, Married())


class GetPregnantLifeEvent(ActionableLifeEvent):
    """Defines an event where two characters stop dating"""

    @classmethod
    def instantiate(
        cls,
        world: World,
        bindings: Optional[RoleList] = None,
    ) -> Optional[ActionableLifeEvent]:

        query = QB.query(
            ("PregnantOne", "Other"),
            QB.with_((GameCharacter, Active, CanGetPregnant), "PregnantOne"),
            QB.not_(QB.with_(Pregnant, "PregnantOne")),
            with_relationship("PregnantOne", "Other", "?relationship"),
            QB.with_((GameCharacter, Active), "Other"),
            QB.or_(
                QB.with_(Dating, "?relationship"),
                QB.with_(Married, "?relationship"),
            ),
        )

        if bindings:
            results = query.execute(world, {r.name: r.gameobject.uid for r in bindings})
        else:
            results = query.execute(world)

        if results:
            chosen_result = world.get_resource(random.Random).choice(results)
            chosen_objects = [world.get_gameobject(uid) for uid in chosen_result]
            roles = dict(zip(query.get_symbols(), chosen_objects))
            return cls(world.get_resource(SimDateTime), [Role(title, gameobject) for title, gameobject in roles.items()])

    def execute(self):
        current_date = self["PregnantOne"].world.get_resource(SimDateTime)
        due_date = current_date.copy()
        due_date.increment(months=9)

        add_status(
            self["PregnantOne"],
            Pregnant(
                partner_id=self["Other"].uid,
                due_date=due_date,
            ),
        )

    def get_priority(self):
        gameobject = self["PregnantOne"]
        children = get_relationships_with_statuses(gameobject, ParentOf)
        if len(children) >= 5:
            return 0.0
        else:
            return 4.0 - len(children) / 8.0


class RetireLifeEvent(ActionableLifeEvent):
    @classmethod
    def instantiate(
        cls,
        world: World,
        bindings: Optional[RoleList] = None,
    ) -> Optional[ActionableLifeEvent]:
        query = QB.query(
            "Retiree",
            QB.with_((GameCharacter, Active, Occupation, Senior), "Retiree"),
            QB.not_(QB.with_(Retired, "Retiree")),
        )

        if bindings:
            results = query.execute(world, {r.name: r.gameobject.uid for r in bindings})
        else:
            results = query.execute(world)

        if results:
            chosen_result = world.get_resource(random.Random).choice(results)
            chosen_objects = [world.get_gameobject(uid) for uid in chosen_result]
            roles = dict(zip(query.get_symbols(), chosen_objects))
            return cls(world.get_resource(SimDateTime), [Role(title, gameobject) for title, gameobject in roles.items()])

    def get_priority(self) -> float:
        return (
            self["Retiree"]
            .world.get_resource(OrreryConfig)
            .settings.get("retirement_prb", 0.4)
        )

    def execute(self) -> None:
        retiree = self["Retiree"]
        add_status(retiree, Retired())

        if business_owner := retiree.try_component(BusinessOwner):
            shutdown_business(retiree.world.get_gameobject(business_owner.business))
        else:
            end_job(retiree, self.get_type())


class FindOwnPlaceLifeEvent(ActionableLifeEvent):
    initiator = "Character"

    @classmethod
    def instantiate(
        cls,
        world: World,
        bindings: Optional[RoleList] = None,
    ) -> Optional[ActionableLifeEvent]:
        query = QB.query(
            "Character",
            QB.from_(FindOwnPlaceLifeEvent.bind_potential_mover, "Character"),
        )

        if bindings:
            results = query.execute(world, {r.name: r.gameobject.uid for r in bindings})
        else:
            results = query.execute(world)

        if results:
            chosen_result = world.get_resource(random.Random).choice(results)
            chosen_objects = [world.get_gameobject(uid) for uid in chosen_result]
            roles = dict(zip(query.get_symbols(), chosen_objects))
            return cls(world.get_resource(SimDateTime), [Role(title, gameobject) for title, gameobject in roles.items()])

    def get_priority(self) -> float:
        return 0.7

    @staticmethod
    def bind_potential_mover(world: World) -> List[Tuple[Any, ...]]:
        eligible: List[Tuple[Any, ...]] = []

        for gid, (_, _, resident, _) in world.get_components(
            (GameCharacter, Occupation, Resident, Active)
        ):
            character = world.get_gameobject(gid)
            if get_life_stage(character) < YoungAdult:
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

    def execute(self):
        # Try to find somewhere to live
        character = self["Character"]
        vacant_residence = FindOwnPlaceLifeEvent.choose_random_vacant_residence(
            character.world
        )
        if vacant_residence:
            # Move into house with any dependent children
            set_residence(character, vacant_residence)

        # Depart if no housing could be found
        else:
            depart_settlement(character.world, character, self.get_type())


class DieOfOldAge(ActionableLifeEvent):
    initiator = "Deceased"

    @classmethod
    def instantiate(
        cls,
        world: World,
        bindings: Optional[RoleList] = None,
    ) -> Optional[ActionableLifeEvent]:
        query = QB.query(
            "Deceased",
            QB.with_((GameCharacter, Active), "Deceased"),
            QB.filter_(
                lambda gameobject: gameobject.get_component(GameCharacter).age
                >= gameobject.get_component(AgingConfig).lifespan,
                "Deceased",
            ),
        )

        if bindings:
            results = query.execute(world, {r.name: r.gameobject.uid for r in bindings})
        else:
            results = query.execute(world)

        if results:
            chosen_result = world.get_resource(random.Random).choice(results)
            chosen_objects = [world.get_gameobject(uid) for uid in chosen_result]
            roles = dict(zip(query.get_symbols(), chosen_objects))
            return cls(world.get_resource(SimDateTime), [Role(title, gameobject) for title, gameobject in roles.items()])

    def get_priority(self) -> float:
        return 0.8

    def execute(self) -> None:
        deceased = self["Deceased"]
        death_event = Die(self.get_timestamp(), deceased)
        deceased.world.get_resource(LifeEventBuffer).append(death_event)
        death_event.execute()


class Die(ActionableLifeEvent):

    initiator = "Character"

    def __init__(self, date: SimDateTime, character: GameObject) -> None:
        super().__init__(timestamp=date, roles=[Role("Character", character)])

    def execute(self) -> None:
        character = self["Character"]

        if character.has_component(Occupation):
            if business_owner := character.try_component(BusinessOwner):
                shutdown_business(
                    character.world.get_gameobject(business_owner.business)
                )
            else:
                end_job(character, reason=self.get_type())

        if character.has_component(Resident):
            set_residence(character, None)

        add_status(character, Deceased())
        clear_frequented_locations(character)
        clear_statuses(character)

        remove_character_from_settlement(character)

    @classmethod
    def instantiate(
        cls,
        world: World,
        bindings: Optional[RoleList] = None,
    ) -> Optional[ActionableLifeEvent]:

        bindings = bindings if bindings else RoleList()

        character = bindings.get("Character")

        if character is None:
            return None

        return cls(
            world.get_resource(SimDateTime),
            character,
        )


class GoOutOfBusiness(ActionableLifeEvent):

    initiator = "Business"
    optional = False

    def execute(self):
        shutdown_business(self["Business"])

    def get_priority(self) -> float:
        business = self["Business"].get_component(Business)
        if business.years_in_business < 5:
            return 0.0
        elif business.years_in_business < business.config.spawning.lifespan:
            return business.years_in_business / business.config.spawning.lifespan
        else:
            return 0.7

    @classmethod
    def instantiate(
        cls,
        world: World,
        bindings: Optional[RoleList] = None,
    ) -> Optional[ActionableLifeEvent]:
        query = QB.query(
            "Business", QB.with_((Business, OpenForBusiness, Active), "Business")
        )

        processed_bindings = (
            {r.name: r.gameobject.uid for r in bindings} if bindings else {}
        )

        if results := query.execute(world, processed_bindings):
            chosen_result = world.get_resource(random.Random).choice(results)
            chosen_objects = [world.get_gameobject(uid) for uid in chosen_result]
            roles = dict(zip(query.get_symbols(), chosen_objects))
            return cls(world.get_resource(SimDateTime), [Role(title, gameobject) for title, gameobject in roles.items()])


class StartBusiness(ActionableLifeEvent):
    """Character is given the option to start a new business"""

    def execute(self) -> None:
        pass

    @classmethod
    def instantiate(
        cls,
        world: World,
        bindings: Optional[RoleList] = None,
    ) -> Optional[ActionableLifeEvent]:
        pass

    # The tuple of the characters that need to approve the life event before
    # it can take place
    needs_approval = ("BusinessOwner",)

    def is_optional(self, role_name: str) -> bool:
        """Returns True if object with the given role needs to approve the event"""
        return role_name in self.needs_approval

    def check_event_preconditions(self, world: World) -> bool:
        """Return True if the preconditions for this event pass"""
        ...

    @staticmethod
    def _cast_business_owner(world: World) -> Generator[GameObject, None, None]:
        candidates = [
            world.get_gameobject(g)
            for g, _ in world.get_components((GameCharacter, InTheWorkforce))
        ]

        candidates = filter(
            lambda g: get_life_stage(g) >= YoungAdult,
            candidates,
        )

        for c in candidates:
            yield c

    @staticmethod
    def _cast_business_type(
        world: World, roles: Dict[str, GameObject]
    ) -> Generator[BusinessPrefab, None, None]:
        candidates = world.get_resource(BusinessLibrary).get_all()
        occupation_types = world.get_resource(OccupationTypeLibrary)

        # Filter for business prefabs that specify owners
        # Filter for all the business types that the potential owner is eligible
        # to own
        candidates = [
            c for c in candidates
            if c.config.owner_type is not None
            and occupation_types.get(c.config.owner_type).precondition(
                roles["BusinessOwner"]
            )
        ]

        for c in candidates:
            yield c


plugin_info: PluginInfo = {
    "name": "default life events plugin",
    "plugin_id": "default.life-events",
    "version": "0.1.0",
}


def setup(sim: Orrery):
    life_event_library = sim.world.get_resource(LifeEventLibrary)

    life_event_library.add(MarriageLifeEvent)
    life_event_library.add(StartDatingLifeEvent)
    life_event_library.add(DatingBreakUp)
    life_event_library.add(DivorceLifeEvent)
    life_event_library.add(GetPregnantLifeEvent)
    life_event_library.add(RetireLifeEvent)
    life_event_library.add(FindOwnPlaceLifeEvent)
    life_event_library.add(DieOfOldAge)
    life_event_library.add(GoOutOfBusiness)
    life_event_library.add(StartBusiness)
