"""
traits.py

The simulation needs another way to handle personality representation aside from
virtues. Traits were supposed to be one of the additional ways that users could
add nuance to how characters treat each other what actions/events they engage in,
and where they choose to frequent within the settlement(s).

Currently, traits are not in use as I have not found the proper representation
for them that would allow user to write rules.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional, Set

from orrery.core.ecs import Component, IComponentFactory, World


@dataclass(frozen=True, slots=True)
class TraitInstance:
    """
    A specific trait held by a character

    Attributes
    ----------
    uid: int
        A unique identifier for this trait
    name: str
        The name of the trait
    excludes: Set[str]
        The set of traits that are not allowed when a character has this trait
    """

    uid: int
    name: str
    excludes: Set[str] = field(default_factory=set)

    def __hash__(self) -> int:
        return self.uid

    def __str__(self) -> str:
        return self.name

    def __eq__(self, other: object) -> bool:
        if isinstance(other, TraitInstance):
            return self.uid == other.uid
        raise TypeError(f"Expected TraitInstance but was {type(object)}")


class TraitLibrary:
    """
    Repository of all the various traits that characters can have

    _traits: Dict[str, TraitInstance]
        All the traits present in the library

    Notes
    -----
    This classes uses the flyweight design pattern to save  memory space since
    many traits are shared between characters.
    """

    __slots__ = "_traits"

    def __init__(self) -> None:
        self._traits: Dict[str, TraitInstance] = {}

    def __contains__(self, trait_name: str) -> bool:
        """Return True there is already a trait with the given name"""
        return trait_name.lower() in self._traits

    def __iter__(self) -> Iterator[TraitInstance]:
        """Return iterator for the ActivityLibrary"""
        return self._traits.values().__iter__()

    def get(self, trait_name: str, create_new: bool = True) -> TraitInstance:
        """
        Get an Activity instance and create a new one if a
        matching instance does not exist
        """
        lc_trait_name = trait_name.lower()

        if lc_trait_name in self._traits:
            return self._traits[lc_trait_name]

        if create_new is False:
            raise KeyError(f"No trait found with name {trait_name}")

        uid = len(self._traits)
        trait = TraitInstance(uid, lc_trait_name)
        self._traits[lc_trait_name] = trait
        return trait


class Traits(Component):
    """Manages the trait instances associated with a character"""

    __slots__ = "_traits"

    def __init__(self, traits: Optional[Set[TraitInstance]] = None) -> None:
        super(Component, self).__init__()
        self._traits: Set[TraitInstance] = set(list(traits if traits else set()))

    def add_trait(self, trait: TraitInstance) -> None:
        self._traits.add(trait)

    def remove_trait(self, trait: TraitInstance) -> None:
        self._traits.remove(trait)

    def __iter__(self) -> Iterator[TraitInstance]:
        return self._traits.__iter__()

    def __contains__(self, trait: TraitInstance) -> bool:
        return trait in self._traits

    def to_dict(self) -> Dict[str, Any]:
        return {"traits": [str(t) for t in self._traits]}


class TraitsFactory(IComponentFactory):
    """Creates instances of Traits components"""

    def create(
        self, world: World, traits: Optional[List[str]] = None, **kwargs: Any
    ) -> Traits:
        trait_names: List[str] = traits if traits else []
        library = world.get_resource(TraitLibrary)
        trait_instances: List[TraitInstance] = [library.get(n) for n in trait_names]
        return Traits(set(trait_instances))
