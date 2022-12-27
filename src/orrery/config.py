import random
from dataclasses import dataclass, field
from typing import Union, Dict

from orrery.activity import Activity, ActivityLibrary
from orrery.ecs import World
from orrery.virtues import VirtueVector


@dataclass(frozen=True)
class RelationshipStatConfig:
    min_value: int = -100
    max_value: int = 100
    changes_with_time: bool = False


@dataclass(frozen=True)
class RelationshipSchema:
    stats: Dict[str, RelationshipStatConfig] = field(default_factory=dict)


@dataclass
class ActivityToVirtueConfig:
    """
    Mapping of activities to character virtues.
    We use this class to determine what activities
    characters like to engage in based on their virtues
    """

    mappings: Dict[Activity, VirtueVector] = field(default_factory=dict)

    def add_by_name(self, world: World, activity_name: str, *virtues: str) -> None:
        """Add a new virtue to the mapping"""
        activity = world.get_resource(ActivityLibrary).get(activity_name)

        self.mappings[activity] = VirtueVector({v: 1 for v in virtues})


@dataclass()
class OrreryConfig:
    seed: Union[str, int] = field(default_factory=lambda: random.randint(0, 9999999))
    relationship_schema: RelationshipSchema = field(default_factory=RelationshipSchema)
