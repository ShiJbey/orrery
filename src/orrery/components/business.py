from __future__ import annotations

import logging
import random
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Type

from orrery.core import query
from orrery.core.config import BusinessConfig
from orrery.core.ecs import (
    Component,
    ComponentBundle,
    GameObject,
    IComponentFactory,
    World,
)
from orrery.core.settlement import Settlement
from orrery.core.time import SimDateTime
from orrery.core.tracery import Tracery

logger = logging.getLogger(__name__)


class Occupation(Component):
    """Information about a character's employment status"""

    __slots__ = "_occupation_type", "_years_held", "_business"

    def __init__(
        self, occupation_type: str, business: int, years_held: float = 0.0
    ) -> None:
        """
        Parameters
        ----------
        occupation_type: str
            The name of the occupation
        business: int
            The business that the character is work for
        years_held: float, optional
            The number of years the character has held this job
            (defaults to 0.0)
        """

        super(Component, self).__init__()
        self._occupation_type: str = occupation_type
        self._business: int = business
        self._years_held: float = years_held

    def to_dict(self) -> Dict[str, Any]:
        """Return serialized dict representation of an Occupation component"""
        return {
            "occupation_type": self._occupation_type,
            "business": self._business,
            "years_held": self._years_held,
        }

    @property
    def business(self) -> int:
        """Get the business the character works for"""
        return self._business

    @property
    def years_held(self) -> float:
        """Get the number of years this character has worked this job"""
        return self._years_held

    @property
    def occupation_type(self) -> str:
        """Get the type of occupation this is"""
        return self._occupation_type

    def set_years_held(self, years: float) -> None:
        """Set the number of years this character has held this job"""
        self._years_held += years

    def __repr__(self) -> str:
        return "Occupation(occupation_type={}, business={}, years_held={})".format(
            self.occupation_type, self.business, self.years_held
        )


@dataclass(frozen=True, slots=True)
class WorkHistoryEntry:
    """
    Record of a job held by a character

    Attributes
    ----------
    occupation_type: str
        The name of the job held
    business: int
        The unique ID of the business the character worked at
    years_held: float
        The number of years the character held this job
    reason_for_leaving: Optional[str]
        Name of the event that caused the character to leave this job
    """

    occupation_type: str
    business: int
    years_held: float
    reason_for_leaving: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Return dictionary representation for serialization"""

        ret = {
            "occupation_type": self.occupation_type,
            "business": self.business,
            "years_held": self.years_held,
            "reason_for_leaving": self.reason_for_leaving,
        }
        return ret


class WorkHistory(Component):
    """Stores information about all the jobs that a character has held"""

    __slots__ = "_chronological_history", "_categorical_history"

    def __init__(self) -> None:
        super(Component, self).__init__()
        self._chronological_history: List[WorkHistoryEntry] = []
        self._categorical_history: Dict[str, List[WorkHistoryEntry]] = {}

    @property
    def entries(self) -> List[WorkHistoryEntry]:
        """Get all WorkHistoryEntries"""
        return self._chronological_history

    def add_entry(
        self,
        occupation_type: str,
        business: int,
        years_held: float,
        reason_for_leaving: str = "",
    ) -> None:
        """
        Add an entry to the work history

        Parameters
        ----------
        occupation_type: str
            The name of the job held
        business: int
            The unique ID of the business the character worked at
        years_held: float
            The number of years the character held this job
        reason_for_leaving: str, optional
            Name of the event that caused the character to leave this job
        """
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
            "history": [entry.to_dict() for entry in self._chronological_history],
        }

    def __len__(self) -> int:
        return len(self._chronological_history)

    def __repr__(self) -> str:
        return "WorkHistory({})".format(
            [e.__repr__() for e in self._chronological_history]
        )


@dataclass(frozen=True, slots=True)
class ServiceType:
    """
    A service that can be offered by a business establishment

    Attributes
    ----------
    uid: int
        The unique ID for this service type (unique only among other service types)
    name: str
        The name of the service offered

    Notes
    -----
    DO NOT INSTANTIATE THIS CLASS DIRECTLY. ServiceType instances are created
    as needed by the ServiceLibrary class
    """

    uid: int
    name: str

    def __hash__(self) -> int:
        return self.uid

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return self.name

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ServiceType):
            return self.uid == other.uid
        raise TypeError(f"Expected ServiceType but was {type(object)}")


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


class Services(Component):
    """
    Tracks the services offered by a business

    Attributes
    ----------
    services: Set[ServiceType]
        The set of services offered by the business
    """

    __slots__ = "services"

    def __init__(self, services: Set[ServiceType]) -> None:
        super().__init__()
        self.services: Set[ServiceType] = services

    def has_service(self, service: ServiceType) -> bool:
        """
        Check if a business offers a service

        Parameters
        ----------
        service: ServiceType
            The service to check for

        Returns
        -------
        bool
            Returns True of the business offers this service
        """
        return service in self.services

    def __repr__(self) -> str:
        return "{}({})".format(self.__class__.__name__, self.services)


class ServicesFactory(IComponentFactory):
    """
    Factory class that creates instances of Services components
    """

    def create(self, world: World, **kwargs: Any) -> Component:
        service_list: List[str] = kwargs.get("services", [])
        service_library = world.get_resource(ServiceLibrary)
        return Services(set([service_library.get(s) for s in service_list]))


class ClosedForBusiness(Component):
    """Tags a business as being closed and no longer active"""

    pass


class OpenForBusiness(Component):
    """Tags a business as being open and active in the simulation"""

    pass


class Business(Component):
    """
    Businesses are owned by and employ characters in the simulation

    Attributes
    ----------
    config: BusinessConfig
        The configuration object associated with this business
    name: str
        The name of the business
    _employees: Dict[int, str]
        Employee GameObject IDs mapped to their occupation type
    _open_positions: Dict[str, int]
        Occupation type names mapped to the number of open positions for that type
    owner: Optional[int]
        The GameObject ID of the character that owns this business
    owner_type: Optional[str]
        The occupation type name of the owner of this business
    years_in_business: float
        The number of years this business was/is active in the simulation
    """

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
        years_in_business: float = 0.0,
    ) -> None:
        super().__init__()
        self.config: BusinessConfig = config
        self.name: str = name
        self.owner_type: Optional[str] = owner_type
        self._open_positions: Dict[str, int] = open_positions if open_positions else {}
        self._employees: Dict[int, str] = {}
        self.owner: Optional[int] = owner
        self.years_in_business: float = years_in_business

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "open_positions": self._open_positions,
            "employees": self.get_employees(),
            "owner": self.owner if self.owner is not None else -1,
            "owner_type": self.owner_type if self.owner_type is not None else "",
            "years_in_business": self.years_in_business,
        }

    def needs_owner(self) -> bool:
        """Returns True if this business needs to hire an owner"""
        return self.owner is None and self.owner_type is not None

    def get_open_positions(self) -> List[str]:
        """Returns all the open job titles"""
        return sum(
            [[title] * count for title, count in self._open_positions.items()], []
        )

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
        return "Business(name={}, owner={}, employees={}, openings={}, years_in_business={})".format(
            self.name,
            self.owner,
            self._employees,
            self._open_positions,
            self.years_in_business,
        )


class BusinessFactory(IComponentFactory):
    """Constructs instances of Business components"""

    def create(self, world: World, **kwargs: Any) -> Component:
        name_pattern: str = kwargs["name"]
        owner_type: str = kwargs.get("owner_type", None)
        employee_types: Dict[str, int] = {**kwargs.get("employees", {})}

        config_name = kwargs["config"]

        config = world.get_resource(BusinessLibrary).get(config_name)

        name_generator = world.get_resource(Tracery)

        return Business(
            config=config,
            name=name_generator.generate(name_pattern),
            owner_type=owner_type,
            open_positions=employee_types,
        )


@dataclass(frozen=True, slots=True)
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


class BusinessComponentBundle(ComponentBundle):
    """
    ComponentBundle for specifically constructing business instances

    Attributes
    ----------
    name: str
        The name of the config associated with this bundle

    Note
    ----
    There really is not an explicit need for this class, but it
    exists if we ever need to do something specific with bundles
    that instantiate business GameObjects
    """

    __slots__ = "name"

    def __init__(
        self, name: str, components: Dict[Type[Component], Dict[str, Any]]
    ) -> None:
        super().__init__(components)
        self.name: str = name


class BusinessLibrary:
    """Collection BusinessComponentBundles and configurations that create business GameObjects"""

    __slots__ = "_registry", "_bundles"

    def __init__(self) -> None:
        self._registry: Dict[str, BusinessConfig] = {}
        self._bundles: Dict[str, BusinessComponentBundle] = {}

    def add(
        self, config: BusinessConfig, bundle: Optional[BusinessComponentBundle] = None
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

    def get_bundle(self, name: str) -> BusinessComponentBundle:
        """Retrieve the ComponentBundle mapped to the given name"""
        return self._bundles[name]

    def get_matching_bundles(self, *bundle_names: str) -> List[BusinessComponentBundle]:
        """Get all component bundles that match the given regex strings"""

        matches: List[BusinessComponentBundle] = []

        for name, bundle in self._bundles.items():
            if any([re.match(pattern, name) for pattern in bundle_names]):
                matches.append(bundle)

        return matches

    def choose_random(
        self, world: World, settlement: GameObject
    ) -> Optional[BusinessComponentBundle]:
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
                settlement_comp.business_counts[config.name]
                < config.spawning.max_instances
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


@dataclass
class BusinessOwner(Component):
    business: int
