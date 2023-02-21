"""
Utility decorators that should assist with content authoring
"""
from typing import Any, Type, TypeVar

from orrery import Component, IComponentFactory, ISystem, Orrery
from orrery.content_management import AIBrainFactory, AIBrainLibrary, LifeEventLibrary
from orrery.core.life_event import LifeEvent

_CT = TypeVar("_CT", bound=Component)
_CF = TypeVar("_CF", bound=IComponentFactory)
_RT = TypeVar("_RT", bound=Any)
_ST = TypeVar("_ST", bound=ISystem)
_LT = TypeVar("_LT", bound=LifeEvent)


def brain_factory(sim: Orrery, name: str):
    def decorator(fn: AIBrainFactory):
        sim.world.get_resource(AIBrainLibrary).add(name, fn)
        return fn

    return decorator


def component(sim: Orrery):
    """Register a component type with the  simulation

    Registers a component class type with the simulation's World instance.
    This allows content authors to use the Component in YAML files and
    EntityPrefabs.

    Parameters
    ----------
    sim: Orrery
        The simulation instance to register the life event to
    """

    def decorator(cls: Type[_CT]) -> Type[_CT]:
        sim.world.register_component(cls)
        return cls

    return decorator


def component_factory(sim: Orrery, component_type: Type[Component], **kwargs: Any):
    """Register a component type with the  simulation

    Registers a component class type with the simulation's World instance.
    This allows content authors to use the Component in YAML files and
    EntityPrefabs.

    Parameters
    ----------
    sim: Orrery
        The simulation instance to register the life event to
    component_type: Type[Component]
        The component type the factory instantiates
    """

    def decorator(cls: Type[_CF]) -> Type[_CF]:
        sim.world.get_component_info(component_type.__name__).factory = cls(**kwargs)
        return cls

    return decorator


def resource(sim: Orrery, **kwargs: Any):
    """Add a class as a shared resource

    This decorator adds an instance of the decorated class as a shared resource.

    Parameters
    ----------
    sim: Orrery
        The simulation instance to register the life event to
    **kwargs: Any
        Keyword arguments to pass to the constructor of the decorated class
    """

    def decorator(cls: Type[_RT]) -> Type[_RT]:
        sim.world.add_resource(cls(**kwargs))
        return cls

    return decorator


def system(sim: Orrery, **kwargs: Any):
    """Add a class as a simulation system

    This decorator adds an instance of the decorated class as a shared resource.

    Parameters
    ----------
    sim: Orrery
        The simulation instance to register the life event to
    **kwargs: Any
        Keyword arguments to pass to the constructor of the decorated class
    """

    def decorator(cls: Type[_ST]) -> Type[_ST]:
        sim.world.add_system(cls(**kwargs))
        return cls

    return decorator


def life_event(sim: Orrery):
    """Add a class as a simulation system

    This decorator adds an instance of the decorated class as a shared resource.

    Parameters
    ----------
    sim: Orrery
        The simulation instance to register the life event to
    """

    def decorator(cls: Type[_LT]) -> Type[_LT]:
        sim.world.get_resource(LifeEventLibrary).add(cls)
        return cls

    return decorator
