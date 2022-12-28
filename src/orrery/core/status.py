from dataclasses import dataclass
from typing import Any, Dict, Tuple, Type

from orrery.core.ecs import Component, ComponentBundle, ISystem


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


class statusDurationSystem(ISystem):
    def process(self, *args: Any, **kwargs: Any):
        for _, status_duration in self.world.get_component(StatusDuration):
            status_duration.elapsed += 1
