from __future__ import annotations

import random
import re
from typing import Dict, Iterator, List, Optional

from orrery.components.activity import ActivityInstance
from orrery.components.business import OccupationType, ServiceType, logger
from orrery.components.settlement import Settlement
from orrery.components.virtues import Virtues
from orrery.core.ecs import GameObject, World
from orrery.core.life_event import ILifeEvent
from orrery.core.social_rule import ISocialRule
from orrery.core.time import SimDateTime
from orrery.prefabs import BusinessPrefab, CharacterPrefab, ResidencePrefab


class ActivityLibrary:
    """
    Repository of all the various activities that can exist
    in the simulated world

    Attributes
    ----------
    _next_id: int
        The unique identifier assigned to the next created
        activity instance
    _name_to_activity: Dict[str, Activity]
        Map of the names of activities to Activity instances
    _id_to_name: Dict[int, str]
        Map of the unique ids of activities to their names

    Notes
    -----
    This classes uses the flyweight design pattern to save
    memory space since many activities are shared between
    location instances.
    """

    __slots__ = "_next_id", "_name_to_activity", "_id_to_name"

    def __init__(self) -> None:
        self._next_id: int = 0
        self._name_to_activity: Dict[str, ActivityInstance] = {}
        self._id_to_name: Dict[int, str] = {}

    def __contains__(self, activity_name: str) -> bool:
        """Return True if a service type exists with the given name"""
        return activity_name.lower() in self._name_to_activity

    def __iter__(self) -> Iterator[ActivityInstance]:
        """Return iterator for the ActivityLibrary"""
        return self._name_to_activity.values().__iter__()

    def get(self, activity_name: str, create_new: bool = True) -> ActivityInstance:
        """
        Get an Activity instance and create a new one if a
        matching instance does not exist
        """
        lc_activity_name = activity_name.lower()

        if lc_activity_name in self._name_to_activity:
            return self._name_to_activity[lc_activity_name]

        if create_new is False:
            raise KeyError(f"No activity found with name {activity_name}")

        uid = self._next_id
        self._next_id = self._next_id + 1
        activity = ActivityInstance(uid, lc_activity_name)
        self._name_to_activity[lc_activity_name] = activity
        self._id_to_name[uid] = lc_activity_name
        return activity


class ActivityToVirtueMap:
    """
    Mapping of activities to character virtues.
    We use this class to determine what activities
    characters like to engage in based on their virtues
    """

    __slots__ = "mappings"

    def __init__(self) -> None:
        self.mappings: Dict[ActivityInstance, Virtues] = {}

    def add_by_name(self, world: World, activity_name: str, *virtues: str) -> None:
        """Add a new virtue to the mapping"""
        activity = world.get_resource(ActivityLibrary).get(activity_name)

        self.mappings[activity] = Virtues({v: 1 for v in virtues})


class ServiceLibrary:
    """
    Repository of various services offered by a business

    Attributes
    ----------
    _next_id: int
        The next ID assigned to a new ServiceType instance
    _services: List[ServiceType]
        A list of all the possible services a business could have
    _name_to_id: Dict[str, int]
        Mapping of service names to indexes into the _services list
    """

    __slots__ = "_next_id", "_services", "_name_to_id"

    def __init__(self) -> None:
        self._next_id: int = 0
        self._services: List[ServiceType] = []
        self._name_to_id: Dict[str, int] = {}

    def __contains__(self, service_name: str) -> bool:
        """Return True if a service type exists with the given name"""
        return service_name.lower() in self._name_to_id

    def get(self, service_name: str) -> ServiceType:
        lc_service_name = service_name.lower()

        if lc_service_name in self._name_to_id:
            return self._services[self._name_to_id[lc_service_name]]

        uid = self._next_id
        self._next_id += 1
        service_type = ServiceType(uid, lc_service_name)
        self._services.append(service_type)
        self._name_to_id[lc_service_name] = uid
        return service_type


class OccupationTypeLibrary:
    """Collection OccupationType information for lookup at runtime"""

    __slots__ = "_registry"

    def __init__(self) -> None:
        self._registry: Dict[str, OccupationType] = {}

    def add(
        self,
        occupation_type: OccupationType,
    ) -> None:
        """
        Add a new occupation type to the library

        Parameters
        ----------
        occupation_type: OccupationType
            The occupation type instance to add
        """
        if occupation_type.name in self._registry:
            logger.debug(f"Overwriting OccupationType: ({occupation_type.name})")
        self._registry[occupation_type.name] = occupation_type

    def get(self, name: str) -> OccupationType:
        """
        Get an OccupationType by name

        Parameters
        ----------
        name: str
            The registered name of the OccupationType

        Returns
        -------
        OccupationType

        Raises
        ------
        KeyError
            When there is not an OccupationType
            registered to that name
        """
        return self._registry[name]


class BusinessLibrary:
    """Collection Business prefabs"""

    __slots__ = "_prefabs"

    def __init__(self) -> None:
        self._prefabs: Dict[str, BusinessPrefab] = {}

    def add(self, prefab: BusinessPrefab) -> None:
        """Add a new prefab

        Parameters
        ----------
        prefab: BusinessPrefab
            The prefab to add
        """
        self._prefabs[prefab.name] = prefab

    def get_all(self) -> List[BusinessPrefab]:
        """Get all stored prefabs"""
        return list(self._prefabs.values())

    def get(self, name: str) -> BusinessPrefab:
        """Get a prefab by name"""
        return self._prefabs[name]

    def get_matching_prefabs(self, *name_patterns: str) -> List[BusinessPrefab]:
        """Get all component bundles that match the given regex strings"""

        matches: List[BusinessPrefab] = []

        for name, prefab in self._prefabs.items():
            if any([re.match(pattern, name) for pattern in name_patterns]):
                matches.append(prefab)

        return matches

    def choose_random(
        self, world: World, settlement: GameObject
    ) -> Optional[BusinessPrefab]:
        """
        Return all business archetypes that may be built
        given the state of the simulation
        """
        settlement_comp = settlement.get_component(Settlement)
        date = world.get_resource(SimDateTime)
        rng = world.get_resource(random.Random)

        choices: List[BusinessPrefab] = []
        weights: List[int] = []

        for prefab in self.get_all():
            if (
                settlement_comp.business_counts[prefab.name]
                < prefab.config.spawning.max_instances
                and settlement_comp.population >= prefab.config.spawning.min_population
                and (
                    prefab.config.spawning.year_available
                    <= date.year
                    < prefab.config.spawning.year_obsolete
                )
                and not prefab.is_template
            ):
                choices.append(prefab)
                weights.append(prefab.config.spawning.spawn_frequency)

        if choices:
            # Choose an archetype at random
            return rng.choices(population=choices, weights=weights, k=1)[0]

        return None


class CharacterLibrary:
    """Collection of factories that create character entities"""

    __slots__ = "_prefabs"

    def __init__(self) -> None:
        self._prefabs: Dict[str, CharacterPrefab] = {}

    def add(self, prefab: CharacterPrefab) -> None:
        """Register a new prefab"""
        self._prefabs[prefab.name] = prefab

    def get_all(self) -> List[CharacterPrefab]:
        """Get all stored archetypes"""
        return list(self._prefabs.values())

    def get(self, name: str) -> CharacterPrefab:
        """Get a prefab by name"""
        return self._prefabs[name]

    def get_matching_prefabs(self, *name_patterns: str) -> List[CharacterPrefab]:
        """Get all component bundles that match the given regex strings"""

        matches: List[CharacterPrefab] = []

        for name, bundle in self._prefabs.items():
            if any([re.match(pattern, name) for pattern in name_patterns]):
                matches.append(bundle)

        return matches

    def choose_random(
        self,
        rng: random.Random,
    ) -> Optional[CharacterPrefab]:
        """Performs a weighted random selection across all character archetypes"""
        choices: List[CharacterPrefab] = []
        weights: List[int] = []

        for prefab in self.get_all():
            if prefab.is_template is False:
                choices.append(prefab)
                weights.append(prefab.config.spawning.spawn_frequency)

        if choices:
            # Choose an archetype at random
            return rng.choices(population=choices, weights=weights, k=1)[0]

        return None


class ResidenceLibrary:
    """Collection factories that create residence entities"""

    __slots__ = "_prefabs"

    def __init__(self) -> None:
        self._prefabs: Dict[str, ResidencePrefab] = {}

    def add(self, prefab: ResidencePrefab) -> None:
        """Register a new prefab"""
        self._prefabs[prefab.name] = prefab

    def get_all(self) -> List[ResidencePrefab]:
        """Get all stored archetypes"""
        return list(self._prefabs.values())

    def get(self, name: str) -> ResidencePrefab:
        """Get a prefab by name"""
        return self._prefabs[name]

    def get_matching_prefabs(self, *name_patterns: str) -> List[ResidencePrefab]:
        """Get all component bundles that match the given regex strings"""

        matches: List[ResidencePrefab] = []

        for name, bundle in self._prefabs.items():
            if any([re.match(pattern, name) for pattern in name_patterns]):
                matches.append(bundle)

        return matches

    def choose_random(
        self,
        rng: random.Random,
    ) -> Optional[ResidencePrefab]:
        """Performs a weighted random selection across all character archetypes"""
        choices: List[ResidencePrefab] = []
        weights: List[int] = []

        for prefab in self.get_all():
            if prefab.is_template is False:
                choices.append(prefab)
                weights.append(prefab.config.spawning.spawn_frequency)

        if choices:
            return rng.choices(population=choices, weights=weights, k=1)[0]

        return None


class LifeEventLibrary:
    """
    Static class used to store instances of LifeEventTypes for
    use at runtime.
    """

    _registry: Dict[str, ILifeEvent] = {}

    @classmethod
    def add(cls, life_event: ILifeEvent, name: Optional[str] = None) -> None:
        """Register a new LifeEventType mapped to a name"""
        key_name = name if name else life_event.get_name()
        cls._registry[key_name] = life_event

    @classmethod
    def get_all(cls) -> List[ILifeEvent]:
        """Get all LifeEventTypes stores in the Library"""
        return list(cls._registry.values())

    @classmethod
    def get(cls, name: str) -> ILifeEvent:
        """Get a LifeEventType using a name"""
        return cls._registry[name]


class SocialRuleLibrary:
    """
    Repository of ISocialRule instances to use during the simulation.

    Attributes
    ----------
    _all_rules: Dict[str, ISocialRule]
        All the rules added to the library, including ones not actively used in
        relationship calculations. (allows filtering)
    _active_rules: List[ISocialRule]
        List of the rules that are actively used for relationship calculations
    _active_rule_names: List[str]
        List of regular expression strings that correspond to rules to
        set as active for use in relationship calculations
    """

    __slots__ = "_all_rules", "_active_rules", "_active_rule_names"

    def __init__(
        self,
        rules: Optional[List[ISocialRule]] = None,
        active_rules: Optional[List[str]] = None,
    ) -> None:
        self._all_rules: Dict[str, ISocialRule] = {}
        self._active_rules: List[ISocialRule] = []
        self._active_rule_names: List[str] = active_rules if active_rules else [".*"]

        if rules:
            for rule in rules:
                self.add(rule)

    def add(self, rule: ISocialRule) -> None:
        """
        Add a rule to the library

        Parameters
        ----------
        rule: ISocialRule
            The rule to add
        """
        self._all_rules[rule.get_uid()] = rule
        if any(
            [re.match(pattern, rule.get_uid()) for pattern in self._active_rule_names]
        ):
            self._active_rules.append(rule)

    def set_active_rules(self, rule_names: List[str]) -> None:
        """
        Sets the rules with names that match the regex strings as active

        Parameters
        ----------
        rule_names: List[str]
            Regex strings for rule names to activate
        """
        self._active_rules.clear()
        self._active_rule_names = rule_names
        for name, rule in self._all_rules.items():
            if any([re.match(pattern, name) for pattern in self._active_rule_names]):
                self._active_rules.append(rule)

    def get_active_rules(self) -> List[ISocialRule]:
        """Return social rules that are active for relationship calculations"""
        return self._active_rules
