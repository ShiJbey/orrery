from typing import Any, Dict, Iterator, List, Optional

from orrery.core.ecs import Component
from orrery.core.social_rule import ISocialRule


class Trait(Component):
    """
    Traits describe a characters personality. They can be used
    to signify a character's tendency toward certain behaviors
    as well as help increase their proclivity toward certain
    behaviors.
    """

    __slots__ = "name", "rules", "location_proclivities"

    def __init__(
        self,
        name: str,
        rules: Optional[List[ISocialRule]] = None,
        location_proclivities: Optional[Dict[str, int]] = None,
    ) -> None:
        self.name: str = name
        self.rules: List[ISocialRule] = rules if rules else []
        self.location_proclivities: Dict[str, int] = (
            location_proclivities if location_proclivities else {}
        )


class TraitManager(Component):
    """Manages the trait instances associated with a character"""

    __slots__ = "_traits"

    def __init__(self) -> None:
        super(Component, self).__init__()
        self._traits: Dict[str, Trait] = {}

    def add_trait(self, trait: Trait) -> None:
        self._traits[trait.name] = trait

    def remove_trait(self, trait_name: str) -> None:
        del self._traits[trait_name]

    def get_trait(self, trait_name: str) -> Optional[Trait]:
        return self._traits.get(trait_name)

    def __iter__(self) -> Iterator[Trait]:
        return self._traits.values().__iter__()

    def __contains__(self, trait_name: str) -> bool:
        return trait_name in self._traits

    def to_dict(self) -> Dict[str, Any]:
        return {"traits": list(self._traits.keys())}
