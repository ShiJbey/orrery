from abc import ABC
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple, Type

from orrery.core.ecs import Component, ComponentBundle, ISystem


@dataclass
class Status(Component):
    """
    Identifies a GameObject as being a status and holds references to callback functions
    """

    component_type: Type[Component]


@dataclass
class StatusDuration(Component):
    duration: int = -1
    elapsed: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "duration": self.duration,
            "elapsed": self.elapsed,
        }


@dataclass
class RelationshipStatus(Component):
    owner: int
    target: int
    component_type: Type[Component]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "owner": self.owner,
            "target": self.target,
            "component_type": self.component_type.__name__,
        }


class StatusBundle(ComponentBundle, ABC):
    def __init__(
        self,
        component_info: Tuple[Type[Component], Dict[str, Any]],
        duration: int = -1,
    ) -> None:
        super().__init__(
            {
                Status: {
                    "component_type": component_info[0],
                },
                StatusDuration: {"duration": duration},
                component_info[0]: {**component_info[1]},
            }
        )


class RelationshipStatusBundle(ComponentBundle):
    def __init__(
        self,
        owner: int,
        target: int,
        component_info: Tuple[Type[Component], Dict[str, Any]],
        duration: int = -1,
    ) -> None:
        super().__init__(
            {
                RelationshipStatus: {
                    "owner": owner,
                    "target": target,
                    "component_type": component_info[0],
                },
                StatusDuration: {"duration": duration},
                component_info[0]: {**component_info[1]},
            }
        )


class StatusManager(Component):
    """
    Helper component that tracks what statuses
    are attached to a GameObject

    Attributes
    ----------
    status_types: Dict[int, Type[StatusType]]
        List of the StatusTypes attached to the GameObject
    """

    __slots__ = "status_types"

    def __init__(self) -> None:
        super().__init__()
        self.status_types: Dict[int, Type[Component]] = {}

    def add(self, status_id: int, status_type: Type[Component]) -> None:
        self.status_types[status_id] = status_type

    def remove(self, status_id: int) -> None:
        """Removes record of status with the given ID"""
        del self.status_types[status_id]

    def remove_type(self, status_type: Type[Component]) -> None:
        status_to_remove: Optional[int] = None

        for s_id, s_type in self.status_types.items():
            if s_type == status_type:
                status_to_remove = s_id
                break

        if status_to_remove is not None:
            self.remove(status_to_remove)

    def __contains__(self, item: Type[Component]) -> bool:
        return item in self.status_types.values()


class statusDurationSystem(ISystem):
    def process(self, *args: Any, **kwargs: Any):
        for _, status_duration in self.world.get_component(StatusDuration):
            status_duration.elapsed += 1
