"""Application bootstrap."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from ._version import __version__
from .globe import prepare_globe_surface
from .session import RegionSession
from .window import MainWindow


def run_gui(
    *,
    cf_version: str = "current",
    profile: str = "default",
    profile_version: str = "current",
    data_directory: str | Path | None = None,
    profile_directories: Sequence[str | Path] | None = None,
    argv: Sequence[str] | None = None,
) -> int:
    """Start the native application and return its process exit status."""

    QCoreApplication.setApplicationName("CF Regions")
    QCoreApplication.setApplicationVersion(__version__)
    application = QApplication(list(argv) if argv is not None else sys.argv)
    prepare_globe_surface()
    window = MainWindow(
        RegionSession(
            cf_version=cf_version,
            profile=profile,
            profile_version=profile_version,
            data_directory=Path(data_directory) if data_directory is not None else None,
            profile_directories=tuple(
                Path(directory) for directory in profile_directories or ()
            ),
        )
    )
    window.show()
    return application.exec()
