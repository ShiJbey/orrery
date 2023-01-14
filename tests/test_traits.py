"""
test_traits.py

Tests orrery.core.traits
"""
from orrery.core.ecs import World
from orrery.core.traits import TraitLibrary, Traits, TraitsFactory


def test_get_trait_from_library() -> None:
    library = TraitLibrary()
    kind_hearted = library.get("Kind-Hearted")
    kind_hearted_other = library.get("kind-hearted")
    likes_eating = library.get("Likes Eating")

    assert kind_hearted is kind_hearted_other
    assert kind_hearted.uid == 0
    assert likes_eating.uid == 1
    assert likes_eating.name == "likes eating"


def test_iterate_library() -> None:
    library = TraitLibrary()
    library.get("Kind")
    library.get("Likes Eating")
    library.get("Drunkard")
    library.get("People Person")
    library.get("Impulsive Shopper")

    all_traits = set([a.name for a in library])
    assert all_traits == {
        "kind",
        "likes eating",
        "drunkard",
        "people person",
        "impulsive shopper",
    }


def test_library_contains() -> None:
    library = TraitLibrary()
    library.get("Kind")
    library.get("Likes Eating")
    library.get("Drunkard")
    library.get("People Person")
    library.get("Impulsive Shopper")

    assert ("kind" in library) is True
    assert ("likes eating" in library) is True
    assert ("people person" in library) is False
    assert ("drunkard" in library) is False


def test_traits_contains() -> None:
    library = TraitLibrary()
    library.get("Kind")
    library.get("Likes Eating")
    library.get("Drunkard")
    library.get("People Person")
    library.get("Impulsive Shopper")

    traits = Traits(
        {
            library.get("Kind"),
            library.get("Likes Eating"),
            library.get("Impulsive Shopper"),
        }
    )

    assert library.get("kind") in traits
    assert library.get("people person") not in traits


def test_traits_to_dict() -> None:

    library = TraitLibrary()
    library.get("Kind")
    library.get("Likes Eating")
    library.get("Drunkard")
    library.get("People Person")
    library.get("Impulsive Shopper")

    traits = Traits(
        {
            library.get("Kind"),
            library.get("Likes Eating"),
            library.get("Impulsive Shopper"),
        }
    )

    assert traits.to_dict() == {"traits": ["kind", "likes eating", "impulsive shopper"]}


def test_traits_factory() -> None:
    world = World()

    library = TraitLibrary()
    library.get("Kind")
    library.get("Likes Eating")
    library.get("Drunkard")
    library.get("People Person")
    library.get("Impulsive Shopper")

    world.add_resource(library)

    world.register_component(Traits, factory=TraitsFactory())

    factory = TraitsFactory()

    traits = factory.create(world, activities=["Kind", "Drunkard"])

    assert library.get("People Person") not in traits
    assert library.get("Drunkard") in traits
    assert library.get("Kind") in traits
