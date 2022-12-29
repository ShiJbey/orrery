from typing import List

from orrery.components.business import InTheWorkforce, Occupation, unemployed_status
from orrery.components.character import Departed
from orrery.components.shared import Active
from orrery.core.ecs import GameObject, World
from orrery.core.event import Event
from orrery.core.status import Status
from orrery.utils.common import add_status, end_job, remove_status, set_residence


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
        add_status(world, character, unemployed_status(336))


def remove_statuses_from_deceased(world: World, event: Event) -> None:
    """Remove all active statuses when characters die"""
    for c in event.get_all("Character"):
        character = world.get_gameobject(c)

        active_statuses: List[GameObject] = []
        for child_gameobject in character.children:
            if child_gameobject.has_component(Status):
                active_statuses.append(child_gameobject)

        for status in active_statuses:
            remove_status(character, status)


def remove_statuses_from_departed(world: World, event: Event) -> None:
    """Remove all active statuses when characters depart"""
    for c in event.get_all("Character"):
        character = world.get_gameobject(c)

        active_statuses: List[GameObject] = []
        for child_gameobject in character.children:
            if child_gameobject.has_component(Status):
                active_statuses.append(child_gameobject)

        for status in active_statuses:
            remove_status(character, status)
