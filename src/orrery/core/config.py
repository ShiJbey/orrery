import random
from typing import Any, Dict, List, Optional, Union

import pydantic

from orrery.core.activity import Activity, ActivityLibrary
from orrery.core.ecs import World
from orrery.core.virtues import VirtueVector


class RelationshipStatConfig(pydantic.BaseModel):
    min_value: int = -100
    max_value: int = 100
    changes_with_time: bool = False


class RelationshipSchema(pydantic.BaseModel):
    stats: Dict[str, RelationshipStatConfig] = pydantic.Field(default_factory=dict)


class ActivityToVirtueMap:
    """
    Mapping of activities to character virtues.
    We use this class to determine what activities
    characters like to engage in based on their virtues
    """
    __slots__ = "mappings"

    def __init__(self) -> None:
        self.mappings: Dict[Activity, VirtueVector] = {}

    def add_by_name(self, world: World, activity_name: str, *virtues: str) -> None:
        """Add a new virtue to the mapping"""
        activity = world.get_resource(ActivityLibrary).get(activity_name)

        self.mappings[activity] = VirtueVector({v: 1 for v in virtues})


class CharacterSpawnConfig(pydantic.BaseModel):
    """
    Configuration data regarding how this archetype should be spawned

    Attributes
    ----------
    spawn_frequency: int
        The relative frequency that this archetype should be
        chosen to spawn into the simulation
    spouse_archetypes: List[str]
        A list of regular expression strings used to match what
        other character archetypes can spawn as this a spouse
        to this character archetype
    chance_spawn_with_spouse: float
        The probability that a character will spawn with a spouse
    max_children_at_spawn: int
        The maximum number of children that a character can spawn
        with regardless of the presence of a spouse
    child_archetypes: List[str]
        A list of regular expression strings used to match what
        other character archetypes can spawn as a child to
        this character archetype
    """

    spawn_frequency: int = 1
    spouse_archetypes: List[str] = pydantic.Field(default_factory=list)
    chance_spawn_with_spouse: float = 0.5
    max_children_at_spawn: int = 3
    child_archetypes: List[str] = pydantic.Field(default_factory=list)


class CharacterAgingConfig(pydantic.BaseModel):
    """
    Defines settings for how LifeStage changes as a function of age
    as well as settings for the character's lifespan
    """

    lifespan: int
    adolescent: int
    young_adult: int
    adult: int
    senior: int


class CharacterConfig(pydantic.BaseModel):
    name: str
    aging: CharacterAgingConfig
    spawning: CharacterSpawnConfig
    template: bool = False
    extends: Optional[str] = None
    components: Dict[str, Dict[str, Any]] = pydantic.Field(default_factory=dict)


class ResidenceSpawnConfig(pydantic.BaseModel):
    """
    Configuration data regarding how this archetype should be spawned

    Attributes
    ----------
    spawn_frequency: int
        The relative frequency that this archetype should be
        chosen to spawn into the simulation
    max_instances: int
        The maximum number of instances of this archetype that may
        exist in the Settlement at any given time
    min_population: int
        The minimum number of characters that need to live in the
        settlement for this business to be available to spawn
    year_available: int
        The simulated year that this business archetype will be
        available to spawn
    year_obsolete: int
        The simulated year that this business archetype will no longer
        be available to spawn
    residential_zoning: ResidentialZoning
        Marks this residence type as single or multi-family housing
    """

    spawn_frequency: int = 1
    max_instances: int = 9999
    min_population: int = 0
    year_available: int = 0
    year_obsolete: int = 9999


class ResidenceConfig(pydantic.BaseModel):
    name: str
    spawning: ResidenceSpawnConfig = pydantic.Field(default_factory=ResidenceSpawnConfig)
    building_components: Dict[str, Dict[str, Any]] = pydantic.Field(default_factory=dict)
    unit_components: Dict[str, Dict[str, Any]] = pydantic.Field(default_factory=dict)
    num_units: int = 1


class BusinessSpawnConfig(pydantic.BaseModel):
    """
    Configuration data regarding how this archetype should be spawned

    Attributes
    ----------
    spawn_frequency: int
        The relative frequency that this archetype should be
        chosen to spawn into the simulation
    max_instances: int
        The maximum number of instances of this archetype that may
        exist in the Settlement at any given time
    min_population: int
        The minimum number of characters that need to live in the
        settlement for this business to be available to spawn
    year_available: int
        The simulated year that this business archetype will be
        available to spawn
    year_obsolete: int
        The simulated year that this business archetype will no longer
        be available to spawn
    """

    spawn_frequency: int = 1
    max_instances: int = 9999
    min_population: int = 0
    year_available: int = 0
    year_obsolete: int = 9999


class BusinessConfig(pydantic.BaseModel):
    name: str
    spawning: BusinessSpawnConfig = pydantic.Field(default_factory=BusinessSpawnConfig)


class OrreryConfig(pydantic.BaseModel):
    seed: Union[str, int] = pydantic.Field(default_factory=lambda: random.randint(0, 9999999))
    relationship_schema: RelationshipSchema = pydantic.Field(default_factory=RelationshipSchema)
    verbose: bool = False
