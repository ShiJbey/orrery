from typing import Type, TypeVar

from orrery.core.ecs import GameObject
from orrery.core.status import Status, StatusManager

_ST = TypeVar("_ST", bound=Status)


def add_status(gameobject: GameObject, status: Status) -> None:
    """
    Add a status to the given GameObject

    Parameters
    ----------
    gameobject: GameObject
        The GameObject to add the status to
    status: Status
        The status to add
    """
    gameobject.get_component(StatusManager).add(gameobject, status)


def get_status(gameobject: GameObject, status_type: Type[_ST]) -> _ST:
    """
    Get a status from the given GameObject

    Parameters
    ----------
    gameobject: GameObject
        The GameObject to add the status to
    status_type: Type[Status]
        The type status of status to retrieve

    Returns
    -------
    Status
        The instance of the desired status type
    """
    return gameobject.get_component(StatusManager).get(status_type)


def remove_status(gameobject: GameObject, status_type: Type[Status]) -> None:
    """
    Remove a status from the given GameObject

    Parameters
    ----------
    gameobject: GameObject
        The GameObject to add the status to
    status_type: Type[Status]
        The status type to remove
    """
    if has_status(gameobject, status_type):
        gameobject.get_component(StatusManager).remove(gameobject, status_type)


def has_status(gameobject: GameObject, status_type: Type[Status]) -> bool:
    """
    Check for a status of a given type

    Parameters
    ----------
    gameobject: GameObject
        The GameObject to add the status to
    status_type: Type[Status]
        The status type to remove

    Returns
    -------
    bool
        Return True if the GameObject has a status
        of the given type
    """
    return status_type in gameobject.get_component(StatusManager)


def clear_statuses(gameobject: GameObject) -> None:
    """
    Remove all statuses from a GameObject

    Parameters
    ----------
    gameobject: GameObject
        The GameObject to clear statuses from
    """
    gameobject.get_component(StatusManager).clear(gameobject)
