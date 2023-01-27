from __future__ import annotations

from orrery.config import BusinessConfig, CharacterConfig, ResidenceConfig
from orrery.core.ecs import EntityPrefab


class BusinessPrefab(EntityPrefab):
    """A prefab that specifically represents a Business that can spawn into the world

    Attributes
    ----------
    name: str
        The prefab's name
    config: BusinessConfig
        Configuration settings
    is_template: bool, optional
        Is this prefab prohibited from being instantiated
        (defaults to False)
    extends: str, optional
        The name of the prefab that this one builds on
    """

    name: str
    config: BusinessConfig
    is_template: bool = False
    extends: str = ""


class CharacterPrefab(EntityPrefab):
    """A prefab that specifically represents a character that can spawn into the world

    Attributes
    ----------
    name: str
        The prefab's name
    config: CharacterConfig
        Configuration settings
    is_template: bool, optional
        Is this prefab prohibited from being instantiated
        (defaults to False)
    extends: str, optional
        The name of the prefab that this one builds on
    """

    name: str
    config: CharacterConfig
    is_template: bool = False
    extends: str = ""


class ResidencePrefab(EntityPrefab):
    """A prefab that specifically represents a residence that can spawn into the world

    Attributes
    ----------
    name: str
        The prefab's name
    config: ResidenceConfig
        Configuration settings
    is_template: bool, optional
        Is this prefab prohibited from being instantiated
        (defaults to False)
    extends: str, optional
        The name of the prefab that this one builds on
    """

    name: str
    config: ResidenceConfig
    is_template: bool = False
    extends: str = ""
