from orrery.components.business import InTheWorkforce, Occupation
from orrery.components.character import Departed, GameCharacter, LifeStage
from orrery.components.shared import Active
from orrery.core.ecs import World
from orrery.core.event import Event
from orrery.statuses import Unemployed
from orrery.utils.common import clear_frequented_locations, end_job, set_residence
from orrery.utils.statuses import add_status, clear_statuses, remove_status


def on_depart_callback(world: World, event: Event) -> None:
    character = world.get_gameobject(event["Character"])
    character.remove_component(Active)
    character.add_component(Departed())


def remove_retired_from_occupation(world: World, event: Event) -> None:
    character = world.get_gameobject(event["Retiree"])
    if character.has_component(Occupation):
        end_job(world, character, reason=event.name)


def remove_deceased_from_occupation(world: World, event: Event) -> None:
    character = world.get_gameobject(event["Character"])
    if character.has_component(Occupation):
        end_job(world, character, reason=event.name)


def remove_departed_from_occupation(world: World, event: Event) -> None:
    for gid in event.get_all("Character"):
        character = world.get_gameobject(gid)
        if character.has_component(Occupation):
            end_job(world, character, reason=event.name)


def remove_deceased_from_residence(world: World, event: Event) -> None:
    character = world.get_gameobject(event["Character"])
    set_residence(world, character, None)


def remove_departed_from_residence(world: World, event: Event) -> None:
    for gid in event.get_all("Character"):
        character = world.get_gameobject(gid)
        set_residence(world, character, None)


def on_become_young_adult(world: World, event: Event) -> None:
    """Enable employment for characters who are new young adults"""
    character = world.get_gameobject(event["Character"])
    character.add_component(InTheWorkforce())

    if not character.has_component(Occupation):
        add_status(character, Unemployed(336))


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
        clear_frequented_locations(world, character)


def remove_frequented_locations_from_departed(world: World, event: Event) -> None:
    """Remove all active statuses when characters depart"""
    for c in event.get_all("Character"):
        character = world.get_gameobject(c)
        clear_frequented_locations(world, character)


def remove_unemployed_status_after_start_job(world: World, event: Event) -> None:
    character = world.get_gameobject(event["Character"])
    remove_status(character, Unemployed)


def add_unemployed_status_after_end_job(world: World, event: Event) -> None:
    character = world.get_gameobject(event["Character"])
    add_status(character, Unemployed(336))


def on_join_settlement(world: World, event: Event) -> None:
    character = world.get_gameobject(event["Character"])
    game_character = character.get_component(GameCharacter)

    # TODO: Remove this callback specific code from the utility function
    if game_character.life_stage >= LifeStage.YoungAdult:
        character.add_component(InTheWorkforce())
        add_status(character, Unemployed(336))