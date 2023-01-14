"""
status.py

Statuses represent temporary states of being for gameobjects. They are updated
every timestep and may be used to represent things like mood, unemployment,
or residential status.

Authors need to extend the Status base class to create new status types
"""
from abc import ABC
from typing import Any, Dict, Iterator, Type, TypeVar, cast

from orrery.core.ecs import Component, GameObject, World
from orrery.core.time import TimeDelta


class Status(ABC):
    def on_add(self, world: World, owner: GameObject) -> None:
        """Function called when the status is added"""
        return

    def on_remove(self, world: World, owner: GameObject) -> None:
        """Function called when the status is removed"""
        return

    def on_update(
        self, world: World, owner: GameObject, elapsed_time: TimeDelta
    ) -> None:
        """Update the given status"""
        return

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.__class__.__name__,
        }


_ST = TypeVar("_ST", bound="Status")


class StatusManager(Component):
    """
    Helper component that tracks what statuses are attached to a GameObject

    Attributes
    ----------
    statuses: Dict[Type[StatusType], Status]
        List of the StatusTypes attached to the GameObject
    """

    __slots__ = "statuses"

    def __init__(self) -> None:
        super(Component, self).__init__()
        self.statuses: Dict[Type[Status], Status] = {}

    def add(self, gameobject: GameObject, status: Status) -> None:
        """Add a status to the manager"""
        self.statuses[type(status)] = status
        status.on_add(gameobject.world, gameobject)

    def get(self, status_type: Type[_ST]) -> _ST:
        """Get the status with the given types"""
        return cast(_ST, self.statuses[status_type])

    def remove(self, gameobject: GameObject, status_type: Type[Status]) -> None:
        """Removes the given status"""
        status = self.statuses[status_type]
        status.on_remove(gameobject.world, gameobject)
        del self.statuses[status_type]

    def clear(self, gameobject: GameObject) -> None:
        """
        Removes all statuses from the given gameobject

        Parameters
        ----------
        gameobject: GameObject
            The GameObject to remove the status from
        """
        statuses_types_to_remove = list(self.statuses.keys())
        for status_type in statuses_types_to_remove:
            self.remove(gameobject, status_type)

    def __contains__(self, item: Type[Status]) -> bool:
        """Check if a status type is attached to the GameObject"""
        return item in self.statuses

    def __iter__(self) -> Iterator[Status]:
        """Returns an iterator for the status types"""
        return self.statuses.values().__iter__()
