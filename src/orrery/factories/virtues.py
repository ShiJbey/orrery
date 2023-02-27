from __future__ import annotations

import logging
import random
from typing import Any, Dict, Optional

from orrery.components.virtues import Virtue, Virtues
from orrery.core.ecs import IComponentFactory, World

logger = logging.getLogger(__name__)


class VirtuesFactory(IComponentFactory):
    def create(
        self,
        world: World,
        n_likes: int = 3,
        n_dislikes: int = 3,
        initialization: str = "random",
        overrides: Optional[Dict[str, int]] = None,
        **kwargs: Any,
    ) -> Virtues:
        """Generate a new set of character values"""
        values_overrides: Dict[str, int] = {}

        if initialization == "zeros":
            pass

        elif initialization == "random":
            rng = world.get_resource(random.Random)

            # Select virtues types
            total_virtues: int = n_likes + n_dislikes
            chosen_virtues = [
                virtue.name for virtue in rng.sample(list(Virtue), total_virtues)
            ]

            # select likes and dislikes
            high_values = rng.sample(chosen_virtues, n_likes)
            low_values = list(set(chosen_virtues) - set(high_values))

            # Generate values for each ([30,50] for high values, [-50,-30] for dislikes)
            for trait in high_values:
                values_overrides[trait] = rng.randint(30, 50)

            for trait in low_values:
                values_overrides[trait] = rng.randint(-50, -30)
        else:
            # Using an unknown virtue doesn't break anything, but we should log it
            logger.warning(f"Unrecognized Virtues initialization '{initialization}'")

        if overrides is not None:
            # Override any values with manually-specified values
            values_overrides = {**values_overrides, **overrides}

        return Virtues(values_overrides)
