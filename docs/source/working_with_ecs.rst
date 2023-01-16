Working with the Entity-Component System
========================================

Orrey uses a custom entity-component system (ECS) to drive things. It is what
allows orrery to be flexible to new content without users needing to extend
the core library code.

ECS seems to be all the rage lately, with Unity introducing entities in its
Data-Oriented Technology Stack and their popularity among rougelike designers.

If you are unfamiliar with ECSs then we will do a brief primer before
explaining how to navigate Orrery's.

General ECS overview
---------------------

ECSs are designed to be an optimization strategy for data-intensive applications
such as games and simulations. The main idea is to separate data from the
processes that operate on that data. Then all similar data structures are stored
together in memory to improve runtime performance by reducing cache misses.

Within an ECS, the world is represented as a collection of entities. Each
entity has a set of components associated with it. Components are collections of
related data that model a particular aspect of the simulation. For example, a
*Position2D* component might contain two numerical values, *x* and *y*. Systems
are functions that manipulate the data within components to update the simulation.

If you want a more in-depth discussion, please refer to this `FAQ article from
the Flecs ECS library <https://github.com/SanderMertens/ecs-faq#what-is-ecs>`_.

Overview of Orrery's ECS
------------------------

Orrery uses a custom entity-component system built on top of
`Esper <https://github.com/benmoran56/esper>`_ that integrates features from
other ECS and component-based architectures, like Unity's *GameObjects* or global
resource object in
`Bevy's ECS <https://bevyengine.org/learn/book/getting-started/ecs/>`_.

GameObjects
^^^^^^^^^^^

In Orrey, we call entities, GameObjects. Each GameObject has a unique integer
identifier, a name, and a collection of components.

Components
^^^^^^^^^^

The Component class is an abstract base class inherited by any object that
is intended to be used as a component. It gives subclasses a reference to
the gameobject reference and provides utility methods for tasks like
serializing to a dictionary object.

Systems
^^^^^^^

Systems are objects that inherit from ``ISystem`` or ``System``. They
override a ``process``/``run`` method that gets called every timestep of
the simulation or on a specified interval. Systems can access GameObjects and
their components by querying the world instance for GameObjects containing
particular components.

Resources
^^^^^^^^^

Resources are shared object instances that are accessible from the world.
Orrery uses resource classes to manage configuration data, authored content,
simulation time, random number generation, and more.

World
^^^^^

The World manages all the active GameObjects, Systems, and Resources. Users
can use the world state to retrieve gameobjects or search for ones that have
certain components.

Getting started
---------------

.. code-block:: python

    import random

    from orrery.core.ecs import World

    # Creates a new world instance
    world = World()

    # Add a random number generator as a global resource
    world.add_resource(random.Random())


    class Actor(Component):

        __slots__ = "name"

        def __init__(self, name: str) -> None:
            super().__init__()
            self.name: str = name


    class Money(Component):

        __slots__ = "dollars"

        def __init__(self, dollars: int) -> None:
            super().__init__()
            self.dollars: int = dollars


    class Job(Component):

        __slots__ = "title", "salary"

        def __init__(self, title: str, salary: int) -> None:
            super().__init__()
            self.title: str = title
            self.salary: int = salary


    class SalarySystem(System):
        """Increases a characters money by their salary amount"""

        def run(self, *args: Any, **kwargs: Any) -> None:
            for guid, (money, job) for self.world.get_component(Money, Job):
                # The code below may give errors in some IDEs because
                # the typing isn't the best for Generic return types.
                # There are two solutions to solve this
                # 1) Add '# type: ignore' to the left of the code
                # 2) Import 'cast' from typing and then
                #    money = cast(Money, money)
                #    job = cast(Job, job)
                money.dollars += job.salary

    # You need to register the component with the world instance
    # to use it with the YAML authoring interface
    world.register_component(Money)

    # Create a new character
    alice = world.spawn_gameobject([
        Actor("Alice"),
        Money(10)
    ])

    # Add the system ti the world
    world.add_system(SalarySystem())

    # Stepping the simulation while Alice has no job will not
    # change her current money
    world.step()

    assert alice.get_component(Money).dollars == 10

    # Adding a Job component makes Alice appear in the SalarySystem's
    # world.get_components(...) query.
    alice.add_component(Job("CEO", 500_000))

    # Now stepping the simulation should allow Alice to get paid
    world.step()

    assert alice.get_component(Money).dollars == 500_010
