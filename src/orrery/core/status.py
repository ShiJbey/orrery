from dataclasses import dataclass
from typing import Any, Dict, Iterator, Tuple, Type

from orrery.core.ecs import Component


@dataclass
class Status(Component):
    """
    Identifies a GameObject as being a status

    Attributes
    ----------
    owner: int
        Who/What owns the status
    component_type: Type[Component]
        The component type that hold status-specific data
    time_active: int
        The amount of time (in months) that this status has been active
    """

    owner: int
    component_type: Type[Component]
    time_active: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "owner": self.owner,
            "component_type": self.component_type.__name__,
            "time_active": self.time_active,
        }


@dataclass
class RelationshipStatus(Component):
    """
    Identifies a GameObject as being a RelationshipStatus

    Attributes
    ----------
    owner: int
        Who/What owns the status
    target: int
        Who/What the status is directed toward
    component_type: Type[Component]
        The component type that hold status-specific data
    time_active: int
        The amount of time (in months) that this status has been active
    """

    owner: int
    target: int
    component_type: Type[Component]
    time_active: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "owner": self.owner,
            "target": self.target,
            "component_type": self.component_type.__name__,
            "time_active": self.time_active,
        }


class StatusManager(Component):
    """
    Helper component that tracks what statuses are attached to a GameObject

    Attributes
    ----------
    status_types: Dict[int, Type[StatusType]]
        List of the StatusTypes attached to the GameObject
    """

    __slots__ = "status_types"

    def __init__(self) -> None:
        super(Component, self).__init__()
        self.status_types: Dict[Type[Component], int] = {}

    def add(self, status_id: int, status_type: Type[Component]) -> None:
        """
        Add a status to the manager

        Parameters
        ----------
        status_id: int
            The identifier for the GameObject with the status component
        status_type: Type[Component]
            The main component with status information
        """
        self.status_types[status_type] = status_id

    def get(self, status_type: Type[Component]) -> int:
        """Get all the present statuses with the given status type"""
        return self.status_types[status_type]

    def remove(self, status_type: Type[Component]) -> None:
        """
        Removes record of status with the given ID

        Parameters
        ----------
        status_type: Type[Component]
            The main component with status information
        """
        del self.status_types[status_type]

    def __contains__(self, item: Type[Component]) -> bool:
        """
        Check if a status type is attached to the GameObject

        Parameters
        ----------
        item: Type[Component]
            The component type to check for

        Returns
        -------
        bool
            Returns True if there is a status with the given component type
        """
        return item in self.status_types.values()

    def __iter__(self) -> Iterator[Tuple[Type[Component], int]]:
        """Returns an iterator for the status types"""
        return self.status_types.items().__iter__()
