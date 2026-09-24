"""Offline native desktop application for :mod:`cfregions`."""

from ._version import __version__
from .app import run_gui

__all__ = ["__version__", "run_gui"]
