"""Command-line entry point for the native desktop application."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from ._version import __version__
from .app import run_gui


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cfregions-gui",
        description="Open the offline native CF Regions map.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--cf-version",
        default="current",
        help="initial CF Standardized Region List version (default: current)",
    )
    parser.add_argument(
        "--profile",
        default="default",
        help="initial spatial interpretation profile ID or alias (default: default)",
    )
    parser.add_argument(
        "--profile-version",
        default="current",
        help="initial spatial interpretation profile version (default: current)",
    )
    parser.add_argument(
        "--data-directory",
        type=Path,
        help="complete external cf-regions data-root override",
    )
    parser.add_argument(
        "--profile-directory",
        type=Path,
        action="append",
        default=[],
        help="add profiles discovered below this directory (repeatable)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Parse command-line options and start the GUI."""

    arguments = _build_parser().parse_args(argv)
    return run_gui(
        cf_version=arguments.cf_version,
        profile=arguments.profile,
        profile_version=arguments.profile_version,
        data_directory=arguments.data_directory,
        profile_directories=arguments.profile_directory,
        argv=["cfregions-gui"],
    )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
