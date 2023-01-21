"""
decorators.py

Decorator functions to assist with authoring content.

The decorators in this file are optional. They were added to help make simulation
scripts more readable.
"""

from typing import Any, Callable, Optional, Type, TypeVar

from orrery.core.ecs import Component, IComponentFactory, ISystem, World
from orrery.core.event import Event, EventHandler
from orrery.orrery import Orrery

_CT = TypeVar("_CT", bound=Component)
_ST = TypeVar("_ST", bound=ISystem)
_RT = TypeVar("_RT", bound=Any)


def component(
    sim: Orrery, name: Optional[str] = None, factory: Optional[IComponentFactory] = None
):
    """Register a component type with the  simulation

    Registers a component class type with the simulation's World instance.
    This allows content authors to use the Component in YAML files and
    ComponentBundles.

    Parameters
    ----------
    sim: Orrery
        A simulation instance
    name: str, optional
        A name to register the component type under (defaults to name of class)
    factory: IComponentFactory, optional
        A factory instance used to construct this component type
        (defaults to DefaultComponentFactory())
    """

    def decorator(cls: Type[_CT]) -> Type[_CT]:
        sim.world.register_component(cls, name, factory)
        return cls

    return decorator


def resource(sim: Orrery, **kwargs: Any):
    """Add a class as a shared resource

    This decorator adds an instance of the decorated class as a shared resource.

    Parameters
    ----------
    sim: Orrery
        A simulation instance
    **kwargs: Any
        Keyword arguments to pass to the constructor of the decorated class
    """

    def decorator(cls: Type[_RT]) -> Type[_RT]:
        sim.world.add_resource(cls(**kwargs))
        return cls

    return decorator


def system(sim: Orrery, priority: int = 0, **kwargs: Any):
    """Add a class as a simulation system

    This decorator adds an instance of the decorated class as a shared resource.

    Parameters
    ----------
    sim: Orrery
        A simulation instance
    priority: int
        The priority of this system.
        The higher the number the sooner it runs at the beginning of a simulation step
    **kwargs: Any
        Keyword arguments to pass to the constructor of the decorated class
    """

    def decorator(cls: Type[_ST]) -> Type[_ST]:
        sim.world.add_system(cls(**kwargs), priority=priority)
        return cls

    return decorator


def event_listener(sim: Orrery, event_name: str):
    """Add a new function as an event listener

    This function adds a function as an event listener for events emitted by the shared
    EventHandler object

    Parameters
    ----------
    sim: Orrery
        A simulation instance
    event_name: str
        The name of the event to subscribe to
    """

    def decorator(cb: Callable[[World, Event], None]) -> Callable[[World, Event], None]:
        sim.world.get_resource(EventHandler).on(event_name, cb)
        return cb

    return decorator
