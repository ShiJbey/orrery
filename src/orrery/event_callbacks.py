from orrery.components.business import Occupation
from orrery.components.character import Departed, GameCharacter, LifeStage
from orrery.components.shared import Active
from orrery.components.statuses import InTheWorkforce, Unemployed
from orrery.core.ecs import World
from orrery.core.event import Event
from orrery.core.time import SimDateTime
from orrery.utils.common import clear_frequented_locations, end_job, set_residence
from orrery.utils.statuses import add_status, clear_statuses, remove_status


def on_depart_callback(world: World, event: Event) -> None:
    date = world.get_resource(SimDateTime)
    character = world.get_gameobject(event["Character"])
    remove_status(character, Active)
    add_status(character, Departed(date.to_iso_str()))


def remove_retired_from_occupation(world: World, event: Event) -> None:
    character = world.get_gameobject(event["Retiree"])
    if character.has_component(Occupation):
        end_job(character, reason=event.name)


def remove_deceased_from_occupation(world: World, event: Event) -> None:
    character = world.get_gameobject(event["Character"])
    if character.has_component(Occupation):
        end_job(character, reason=event.name)


def remove_departed_from_occupation(world: World, event: Event) -> None:
    for gid in event.get_all("Character"):
        character = world.get_gameobject(gid)
        if character.has_component(Occupation):
            end_job(character, reason=event.name)


def remove_deceased_from_residence(world: World, event: Event) -> None:
    character = world.get_gameobject(event["Character"])
    set_residence(world, character, None)


def remove_departed_from_residence(world: World, event: Event) -> None:
    for gid in event.get_all("Character"):
        character = world.get_gameobject(gid)
        set_residence(world, character, None)


def on_become_young_adult(world: World, event: Event) -> None:
    """Enable employment for characters who are new young adults"""
    date = world.get_resource(SimDateTime)
    character = world.get_gameobject(event["Character"])
    add_status(character, InTheWorkforce(date.to_iso_str()))

    if not character.has_component(Occupation):
        add_status(character, Unemployed(date.to_iso_str()))


def remove_statuses_from_deceased(world: World, event: Event) -> None:
    """Remove all active statuses when characters die"""
    for c in event.get_all("Character"):
        character = world.get_gameobject(c)
        clear_statuses(character)


def remove_statuses_from_departed(world: World, event: Event) -> None:
    """Remove all active statuses when characters depart"""
    for c in event.get_all("Character"):
        character = world.get_gameobject(c)
        clear_statuses(character)


def remove_frequented_locations_from_deceased(world: World, event: Event) -> None:
    """Remove all active statuses when characters die"""
    for c in event.get_all("Character"):
        character = world.get_gameobject(c)
        clear_frequented_locations(character)


def remove_frequented_locations_from_departed(world: World, event: Event) -> None:
    """Remove all active statuses when characters depart"""
    for c in event.get_all("Character"):
        character = world.get_gameobject(c)
        clear_frequented_locations(character)


def on_join_settlement(world: World, event: Event) -> None:
    date = world.get_resource(SimDateTime)
    character = world.get_gameobject(event["Character"])
    game_character = character.get_component(GameCharacter)

    if game_character.life_stage >= LifeStage.YoungAdult:
        add_status(character, InTheWorkforce(date.to_iso_str()))
        if not character.has_component(Occupation):
            add_status(character, Unemployed(date.to_iso_str()))
