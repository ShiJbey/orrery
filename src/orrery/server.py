import threading
from typing import Any, Optional

from flask import Flask
from flask_restful import Api, Resource

from orrery.core.ecs import World
from orrery.data_collection import DataCollector
from orrery.orrery import Orrery, OrreryConfig


class GameObjectResource(Resource):

    world: World

    def get(self, guid: int):
        return self.world.get_gameobject(guid).to_dict()


class ComponentResource(Resource):

    world: World

    def get(self, guid: int, **kwargs: Any):
        return (
            self.world.get_gameobject(guid)
            .get_component(
                self.world.get_component_info(kwargs["component_type"]).component_type
            )
            .to_dict()
        )


class AllGameObjectsResource(Resource):

    world: World

    def get(self):
        return {"gameobjects": [g.uid for g in self.world.get_gameobjects()]}


class DatatablesResource(Resource):

    world: World

    def get(self, table_name: str):
        return (
            self.world.get_resource(DataCollector)
            .get_table_dataframe(table_name)
            .to_dict()
        )


def run_api_server(sim: Orrery) -> None:
    server: Flask = Flask("Orrery")
    api: Api = Api(server)

    GameObjectResource.world = sim.world
    ComponentResource.world = sim.world
    AllGameObjectsResource.world = sim.world
    DatatablesResource.world = sim.world

    api.add_resource(GameObjectResource, "/api/gameobject/<int:guid>")
    api.add_resource(
        ComponentResource,
        "/api/gameobject/<int:guid>/component/<string:component_type>",
    )
    api.add_resource(
        AllGameObjectsResource,
        "/api/gameobject/",
    )
    api.add_resource(
        DatatablesResource,
        "/api/data/<string:table_name>",
    )

    server.run(debug=False)


def run_simulation(sim: Orrery) -> None:
    print(id(sim.world))


class OrreryServer:
    def __init__(self, config: Optional[OrreryConfig] = None):
        self.sim: Orrery = Orrery(config)

        self.server_thread = threading.Thread(target=run_api_server, args=(self.sim,))

        self.simulation_thread = threading.Thread(
            target=run_simulation, args=(self.sim,)
        )

    def run(self) -> None:
        try:
            self.server_thread.start()
            self.simulation_thread.start()
            while True:
                pass
            # self.server.run(debug=debug)
        except KeyboardInterrupt:
            self.server_thread.join()
            self.simulation_thread.join()
        except SystemExit:
            self.server_thread.join()
            self.simulation_thread.join()
        except SystemError:
            self.server_thread.join()
            self.simulation_thread.join()
