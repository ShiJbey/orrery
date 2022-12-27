from __future__ import annotations

import argparse
import sys

import orrery
import orrery.orrery


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


def run_cli():
    args = get_args()

    if args.version:
        print(orrery.__version__)
        sys.exit(0)
