"""
Utility decorators that should assist with content authoring
"""
from orrery import Orrery
from orrery.content_management import AIBrainFactory, AIBrainLibrary


def brain_factory(sim: Orrery, name: str):
    def decorator(fn: AIBrainFactory):
        sim.world.get_resource(AIBrainLibrary).add(name, fn)
        return fn

    return decorator
