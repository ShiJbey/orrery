from dataclasses import dataclass

from orrery.core.ecs import GameObject, World
from orrery.core.relationship import Relationship, RelationshipStatus
from orrery.core.time import DAYS_PER_MONTH, TimeDelta


@dataclass
class Married(RelationshipStatus):
    """Tags two characters as being married"""

    time_active: float = 0

    def on_update(
        self,
        world: World,
        owner: GameObject,
        relationship: Relationship,
        elapsed_time: TimeDelta,
    ) -> None:
        self.time_active += elapsed_time.total_days / DAYS_PER_MONTH


@dataclass
class Dating(RelationshipStatus):
    """Tags two characters as dating"""

    time_active: float = 0

    def on_update(
        self,
        world: World,
        owner: GameObject,
        relationship: Relationship,
        elapsed_time: TimeDelta,
    ) -> None:
        self.time_active += elapsed_time.total_days / DAYS_PER_MONTH
