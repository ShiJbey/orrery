from __future__ import annotations

import logging
import math
import random
import re
from abc import ABC
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from orrery.core import query
from orrery.core.config import BusinessConfig
from orrery.core.ecs import Component, ComponentBundle, GameObject, IComponentFactory, World
from orrery.core.event import Event
from orrery.core.settlement import Settlement
from orrery.core.status import StatusBundle
from orrery.core.time import SimDateTime
from orrery.core.tracery import Tracery

logger = logging.getLogger(__name__)


class Occupation(Component):
    """
    Employment Information about an entity
    """

    __slots__ = "_occupation_type", "_years_held", "_business", "_level"

    def __init__(
        self,
        occupation_type: str,
        business: int,
        level: int,
    ) -> None:
        super().__init__()
        self._occupation_type: str = occupation_type
        self._business: int = business
        self._level: int = level
        self._years_held: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            **super().to_dict(),
            "occupation_type": self._occupation_type,
            "level": self._level,
            "business": self._business,
            "years_held": self._years_held,
        }

    @property
    def business(self) -> int:
        return self._business

    @property
    def years_held(self) -> int:
        return math.floor(self._years_held)

    @property
    def level(self) -> int:
        return self._level

    @property
    def occupation_type(self) -> str:
        return self._occupation_type

    def increment_years_held(self, years: float) -> None:
        self._years_held += years

    def __repr__(self) -> str:
        return "Occupation(occupation_type={}, business={}, level={}, years_held={})".format(
            self.occupation_type, self.business, self.level, self.years_held
        )


@dataclass
class WorkHistoryEntry:
    """Record of a job held by an entity"""

    occupation_type: str
    business: int
    years_held: float
    reason_for_leaving: Optional[Event] = None

    def to_dict(self) -> Dict[str, Any]:
        """Return dictionary representation for serialization"""

        ret = {
            "occupation_type": self.occupation_type,
            "business": self.business,
            "years_held": self.years_held,
        }

        if self.reason_for_leaving:
            # This should probably point to a unique ID for the
            # event, but we will leave it as the name of the event for now
            ret["reason_for_leaving"] = self.reason_for_leaving.name

        return ret

    def __repr__(self) -> str:
        return "WorkHistoryEntry(type={}, business={}, years_held={})".format(
            self.occupation_type,
            self.business,
            self.years_held,
        )


class WorkHistory(Component):
    """
    Stores information about all the jobs that an entity
    has held

    Attributes
    ----------
    _chronological_history: List[WorkHistoryEntry]
        List of previous job in order from oldest to most recent
    """

    __slots__ = "_chronological_history", "_categorical_history"

    def __init__(self) -> None:
        super(Component, self).__init__()
        self._chronological_history: List[WorkHistoryEntry] = []
        self._categorical_history: Dict[str, List[WorkHistoryEntry]] = {}

    @property
    def entries(self) -> List[WorkHistoryEntry]:
        return self._chronological_history

    def add_entry(
        self,
        occupation_type: str,
        business: int,
        years_held: float,
        reason_for_leaving: Optional[Event] = None,
    ) -> None:
        """Add an entry to the work history"""
        entry = WorkHistoryEntry(
            occupation_type=occupation_type,
            business=business,
            years_held=years_held,
            reason_for_leaving=reason_for_leaving,
        )

        self._chronological_history.append(entry)

        if occupation_type not in self._categorical_history:
            self._categorical_history[occupation_type] = []

        self._categorical_history[occupation_type].append(entry)

    def get_last_entry(self) -> Optional[WorkHistoryEntry]:
        """Get the latest entry to WorkHistory"""
        if self._chronological_history:
            return self._chronological_history[-1]
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            **super().to_dict(),
            "history": [entry.to_dict() for entry in self._chronological_history],
        }

    def __len__(self) -> int:
        return len(self._chronological_history)

    def __repr__(self) -> str:
        return "WorkHistory({})".format(
            [e.__repr__() for e in self._chronological_history]
        )


class ServiceType:
    """A service that can be offered by a business establishment"""

    __slots__ = "_uid", "_name"

    def __init__(self, uid: int, name: str) -> None:
        self._uid = uid
        self._name = name

    @property
    def uid(self) -> int:
        return self._uid

    @property
    def name(self) -> str:
        return self._name

    def __hash__(self) -> int:
        return self._uid

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ServiceType):
            return self.uid == other.uid
        raise TypeError(f"Expected ServiceType but was {type(object)}")


class ServiceTypes:
    """
    Repository of various services offered
    """

    _next_id: int = 1
    _name_to_service: Dict[str, ServiceType] = {}
    _id_to_name: Dict[int, str] = {}

    @classmethod
    def __contains__(cls, service_name: str) -> bool:
        """Return True if a service type exists with the given name"""
        return service_name.lower() in cls._name_to_service

    @classmethod
    def get(cls, service_name: str) -> ServiceType:
        lc_service_name = service_name.lower()

        if lc_service_name in cls._name_to_service:
            return cls._name_to_service[lc_service_name]

        uid = cls._next_id
        cls._next_id = cls._next_id + 1
        service_type = ServiceType(uid, lc_service_name)
        cls._name_to_service[lc_service_name] = service_type
        cls._id_to_name[uid] = lc_service_name
        return service_type


class Services(Component):
    __slots__ = "_services"

    def __init__(self, services: Set[ServiceType]) -> None:
        super().__init__()
        self._services: Set[ServiceType] = services

    def __contains__(self, service_name: str) -> bool:
        return ServiceTypes.get(service_name) in self._services

    def has_service(self, service: ServiceType) -> bool:
        return service in self._services


class ServicesFactory(IComponentFactory):
    def create(self, world: World, **kwargs: Any) -> Component:
        service_list: List[str] = kwargs.get("services", [])
        return Services(set([ServiceTypes.get(s) for s in service_list]))


class ClosedForBusiness(Component):
    pass


class OpenForBusiness(Component):
    __slots__ = "duration"

    def __init__(self) -> None:
        super().__init__()
        self.duration: float = 0.0


class IBusinessType(Component, ABC):
    """Empty interface for creating types of businesses like Restaurants, ETC"""

    pass


class Business(Component):
    __slots__ = (
        "config",
        "name",
        "_employees",
        "_open_positions",
        "owner",
        "owner_type",
        "years_in_business",
    )

    def __init__(
        self,
        config: BusinessConfig,
        name: str,
        owner_type: Optional[str] = None,
        owner: Optional[int] = None,
        open_positions: Optional[Dict[str, int]] = None,
    ) -> None:
        super().__init__()
        self.config: BusinessConfig = config
        self.name: str = name
        self.owner_type: Optional[str] = owner_type
        self._open_positions: Dict[str, int] = open_positions if open_positions else {}
        if owner_type is not None:
            if owner_type in self._open_positions:
                self._open_positions[owner_type] += 1
            else:
                self._open_positions[owner_type] = 0
        self._employees: Dict[int, str] = {}
        self.owner: Optional[int] = owner
        self.years_in_business: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            **super().to_dict(),
            "name": self.name,
            "open_positions": self._open_positions,
            "employees": self.get_employees(),
            "owner": self.owner if self.owner is not None else -1,
            "owner_type": self.owner_type if self.owner_type is not None else "",
        }

    def needs_owner(self) -> bool:
        return self.owner is None and self.owner_type is not None

    def get_open_positions(self) -> List[str]:
        return [title for title, n in self._open_positions.items() if n > 0]

    def get_employees(self) -> List[int]:
        """Return a list of IDs for current employees"""
        return list(self._employees.keys())

    def set_owner(self, owner: Optional[int]) -> None:
        """Set the ID for the owner of the business"""
        self.owner = owner

    def add_employee(self, character: int, position: str) -> None:
        """Add entity to employees and remove a vacant position"""
        self._employees[character] = position
        self._open_positions[position] -= 1

    def remove_employee(self, character: int) -> None:
        """Remove an entity as an employee and add a vacant position"""
        position = self._employees[character]
        del self._employees[character]
        self._open_positions[position] += 1

    def __repr__(self) -> str:
        """Return printable representation"""
        return "Business(name={}, owner={}, employees={}, openings={})".format(
            self.name,
            self.owner,
            self._employees,
            self._open_positions,
        )


class BusinessFactory(IComponentFactory):
    def create(self, world: World, **kwargs: Any) -> Component:
        name_pattern: str = kwargs["name"]
        owner_type: str = kwargs.get("owner_type", None)
        employee_types: Dict[str, int] = kwargs.get("employees", {})

        config_name = kwargs["config"]

        config = world.get_resource(BusinessLibrary).get(config_name)

        name_generator = world.get_resource(Tracery)

        return Business(
            config=config,
            name=name_generator.generate(name_pattern),
            owner_type=owner_type,
            open_positions=employee_types,
        )


class InTheWorkforce(Component):
    """Tags a character as being eligible to work"""

    pass


@dataclass
class OccupationType:
    """
    Shared information about all occupations with this type

    Attributes
    ----------
    name: str
        Name of the position
    level: int
        Prestige or socioeconomic status associated with the position
    precondition: Optional[IOccupationPreconditionFn]
        Function that determines of a candidate gameobject meets th requirements
        of the occupation
    """

    name: str
    level: int = 1
    description: str = ""
    precondition: Optional[query.QueryFilterFn] = None

    def __repr__(self) -> str:
        return f"OccupationType(name={self.name}, level={self.level})"


class OccupationTypeLibrary:
    """Collection OccupationType information for lookup at runtime"""

    __slots__ = "_registry"

    def __init__(self) -> None:
        self._registry: Dict[str, OccupationType] = {}

    def add(
        self,
        occupation_type: OccupationType,
        name: Optional[str] = None,
    ) -> None:
        entry_key = name if name else occupation_type.name
        if entry_key in self._registry:
            logger.debug(f"Overwriting OccupationType: ({entry_key})")
        self._registry[entry_key] = occupation_type

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
    """Collection factories that create business entities"""

    __slots__ = "_registry", "_bundles"

    def __init__(self) -> None:
        self._registry: Dict[str, BusinessConfig] = {}
        self._bundles: Dict[str, ComponentBundle] = {}

    def add(
        self, config: BusinessConfig, bundle: Optional[ComponentBundle] = None
    ) -> None:
        """Register a new archetype by name"""
        self._registry[config.name] = config
        if bundle:
            self._bundles[config.name] = bundle

    def get_all(self) -> List[BusinessConfig]:
        """Get all stored archetypes"""
        return list(self._registry.values())

    def get(self, name: str) -> BusinessConfig:
        """Get an archetype by name"""
        return self._registry[name]

    def get_bundle(self, name: str) -> ComponentBundle:
        """Retrieve the ComponentBundle mapped to the given name"""
        return self._bundles[name]

    def get_matching_bundles(self, *bundle_names: str) -> List[ComponentBundle]:
        """Get all component bundles that match the given regex strings"""

        matches: List[ComponentBundle] = []

        for name, bundle in self._bundles.items():
            if any([re.match(pattern, name) for pattern in bundle_names]):
                matches.append(bundle)

        return matches

    def choose_random(self, world: World, settlement: GameObject) -> Optional[ComponentBundle]:
        """
        Return all business archetypes that may be built
        given the state of the simulation
        """
        settlement_comp = settlement.get_component(Settlement)
        date = world.get_resource(SimDateTime)
        rng = world.get_resource(random.Random)

        choices: List[BusinessConfig] = []
        weights: List[int] = []

        for config in self.get_all():
            if (
                settlement_comp.business_counts[config.name] < config.spawning.max_instances
                and settlement_comp.population >= config.spawning.min_population
                and (
                    config.spawning.year_available
                    <= date.year
                    < config.spawning.year_obsolete
                )
                and not config.template
            ):
                choices.append(config)
                weights.append(config.spawning.spawn_frequency)

        if choices:
            # Choose an archetype at random
            chosen = rng.choices(population=choices, weights=weights, k=1)[0]
            return self._bundles[chosen.name]

        return None


class Unemployed(Component):
    __slots__ = "days_to_find_a_job", "grace_period"

    def __init__(self, days_to_find_a_job: int) -> None:
        super(Component, self).__init__()
        self.days_to_find_a_job: float = float(days_to_find_a_job)
        self.grace_period: float = float(days_to_find_a_job)

    def to_dict(self) -> Dict[str, Any]:
        return {"days_to_find_a_job": self.days_to_find_a_job}


def unemployed_status(days_to_find_a_job: int) -> ComponentBundle:
    return StatusBundle((Unemployed, {"days_to_find_a_job": days_to_find_a_job}))
