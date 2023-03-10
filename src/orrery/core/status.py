"""
status.py

Statuses represent temporary states of being for gameobjects. They are meant to
be paired with systems and updated every timestep and may be used to represent
temporary states like mood, unemployment, pregnancies, etc.
"""
from abc import ABC
from typing import Any, Dict, Iterator, List, Type

from ordered_set import OrderedSet

from orrery.core.ecs import Component


class StatusComponent(Component, ABC):
    """
    A component that tracks a temporary state of being for an entity

    Attributes
    ----------
    created: str
        A timestamp of when this status was created
    """

    __slots__ = "created"

    def __init__(self, created: str) -> None:
        super().__init__()
        self.created: str = created

    def to_dict(self) -> Dict[str, Any]:
        return {"created": self.created}


class StatusManager(Component):
    """Manages the state of statuses attached to the GameObject"""

    __slots__ = "_statuses"

    def __init__(self) -> None:
        super().__init__()
        self._statuses: OrderedSet[Type[StatusComponent]] = OrderedSet([])

    def get_all(self) -> List[Type[StatusComponent]]:
        """Return all the statuses in the tracker"""
        return list(self._statuses)

    def add(self, status_type: Type[StatusComponent]) -> None:
        """Add a status type to the tracker

        Parameters
        ----------
        status_type: Type[Component]
            The status type added to the GameObject
        """
        self._statuses.add(status_type)

    def has(self, status_type: Type[StatusComponent]) -> bool:
        """Check if a status type is active

        Parameters
        ----------
        status_type: Type[Component]
            The status type added to the GameObject

        Returns
        -------
        bool
            True if the status is present
        """
        return status_type in self

    def remove(self, status_type: Type[StatusComponent]) -> None:
        """Remove a status type from the tracker

        Parameters
        ----------
        status_type: Type[Component]
            The status type to be removed from the GameObject
        """
        self._statuses.remove(status_type)

    def clear(self) -> None:
        """Removes all statuses from the tracker gameobject"""
        self._statuses.clear()

    def __contains__(self, item: Type[StatusComponent]) -> bool:
        """Check if a status type is attached to the GameObject"""
        return item in self._statuses

    def __iter__(self) -> Iterator[Type[StatusComponent]]:
        """Return iterator to active status types"""
        return self._statuses.__iter__()

    def __repr__(self) -> str:
        return "{}({})".format(self.__class__.__name__, self._statuses)

    def to_dict(self) -> Dict[str, Any]:
        return {"statuses": [s.__name__ for s in self._statuses]}
