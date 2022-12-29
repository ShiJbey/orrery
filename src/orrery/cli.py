from __future__ import annotations

import argparse
import importlib
import json
import os
import pathlib
import sys
from typing import Any, Dict, Optional

import yaml

from orrery import __version__
from orrery.core.config import OrreryCLIConfig
from orrery.exporter import OrreryJsonExporter
from orrery.orrery import Orrery, Plugin, PluginSetupError


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser("The Orrery commandline interface")

    parser.add_argument(
        "-v",
        "--version",
        action="store_true",
        default=False,
        help="Print the version of Orrery",
    )

    parser.add_argument(
        "-c",
        "--config",
        help="Path to the configuration file to load before running",
    )

    parser.add_argument("-o", "--output", help="path to write final simulation state")

    parser.add_argument(
        "--no-emit",
        default=False,
        action="store_true",
        help="Disable creating an output file with the simulation's final state",
    )

    parser.add_argument(
        "-q",
        "--quiet",
        default=False,
        action="store_true",
        help="Disable all printing to stdout",
    )

    return parser.parse_args()


def load_config_from_path(config_path: str) -> Dict[str, Any]:
    """
    This function loads the configuration file at the given path

    Parameters
    ----------
    config_path: str
        Path to a configuration file to load
    """
    path = pathlib.Path(os.path.abspath(config_path))

    with open(path, "r") as f:
        if path.suffix.lower() == ".json":
            return json.load(f)
        elif path.suffix.lower() == ".yaml":
            return yaml.safe_load(f)
        else:
            raise ValueError(
                f"Attempted to load config from incorrect file type: {path.suffix}."
            )


def try_load_local_config() -> Optional[Dict[str, Any]]:
    """
    Attempt to load a configuration file in the current working
    directory.
    """
    config_load_precedence = [
        os.path.join(os.getcwd(), "neighborly.config.yaml"),
        os.path.join(os.getcwd(), "neighborly.config.yml"),
        os.path.join(os.getcwd(), "neighborly.config.json"),
    ]

    for path in config_load_precedence:
        if os.path.exists(path):
            return load_config_from_path(path)

    return None


def load_plugin(module_name: str, path: Optional[str] = None, **kwargs: Any) -> Plugin:
    """
    Load a plugin

    Parameters
    ----------
    module_name: str
        Name of module to load
    path: Optional[str]
        Path where the Python module lives
    """
    path_prepended = False

    if path:
        path_prepended = True
        plugin_abs_path = os.path.abspath(path)
        sys.path.insert(0, plugin_abs_path)

    try:
        plugin_module = importlib.import_module(module_name)
        plugin: Plugin = getattr(plugin_module, "get_plugin")()
        return plugin
    except KeyError:
        raise PluginSetupError(
            f"'get_plugin' function not found for plugin: {module_name}"
        )
    finally:
        # Remove the given plugin path from the front
        # of the system path to prevent module resolution bugs
        if path_prepended:
            sys.path.pop(0)


def run():
    args = get_args()

    if args.version:
        print(__version__)
        sys.exit(0)

    config = OrreryCLIConfig(years_to_simulate=10)

    if args.config:
        config = OrreryCLIConfig.from_partial(
            load_config_from_path(args.config), config
        )
        config.path = os.path.abspath(args.config)
    else:
        loaded_settings = try_load_local_config()
        if loaded_settings:
            config = OrreryCLIConfig.from_partial(loaded_settings, config)

    config.verbose = not not args.quiet

    sim = Orrery(config)

    for plugin_entry in config.plugins:
        if isinstance(plugin_entry, str):
            plugin = load_plugin(plugin_entry)
            sim.load_plugin(plugin)
        else:
            plugin = load_plugin(plugin_entry.name, plugin_entry.path)
            sim.load_plugin(plugin, **plugin_entry.options)

    sim.run_for(config.years_to_simulate)

    if not args.no_emit:
        output_path = args.output if args.output else f"orrery_{sim.config.seed}.json"

        with open(output_path, "w") as f:
            data = OrreryJsonExporter().export(sim)
            f.write(data)
