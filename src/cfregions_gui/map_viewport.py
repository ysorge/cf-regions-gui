"""Map-scoped controls overlaid on the native map viewport."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Signal
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .map_views import MapViews


class MapViewport(QWidget):
    """Present map-only actions as compact controls inside the map area."""

    mode_requested = Signal(str)

    def __init__(self, map_views: MapViews, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._map = map_views
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(map_views)

        self._navigation = self._control_frame()
        navigation_layout = QHBoxLayout(self._navigation)
        navigation_layout.setContentsMargins(3, 3, 3, 3)
        navigation_layout.setSpacing(2)
        self.world_button = self._button("World", "Reset to the world view", map_views.reset_view)
        self.fit_button = self._button(
            "Fit region",
            "Fit the selected region",
            map_views.fit_selected,
        )
        self.zoom_out_button = self._button("-", "Zoom out", map_views.zoom_out)
        self.zoom_in_button = self._button("+", "Zoom in", map_views.zoom_in)
        for button in (
            self.world_button,
            self.fit_button,
            self.zoom_out_button,
            self.zoom_in_button,
        ):
            navigation_layout.addWidget(button)

        self._view_switch: QFrame | None = None
        self.map_2d_button: QToolButton | None = None
        self.globe_button: QToolButton | None = None
        if map_views.has_globe:
            self._view_switch = self._control_frame()
            view_layout = QHBoxLayout(self._view_switch)
            view_layout.setContentsMargins(3, 3, 3, 3)
            view_layout.setSpacing(0)
            view_group = QButtonGroup(self)
            view_group.setExclusive(True)
            self.map_2d_button = self._mode_button("2D map", "2d")
            self.globe_button = self._mode_button("3D globe", "globe")
            self.map_2d_button.setChecked(True)
            view_group.addButton(self.map_2d_button)
            view_group.addButton(self.globe_button)
            view_layout.addWidget(self.map_2d_button)
            view_layout.addWidget(self.globe_button)

        self._position_controls()

    def _control_frame(self) -> QFrame:
        frame = QFrame(self)
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setAutoFillBackground(True)
        frame.raise_()
        return frame

    @staticmethod
    def _button(text: str, tooltip: str, callback: Callable[[], None]) -> QToolButton:
        button = QToolButton()
        button.setText(text)
        button.setToolTip(tooltip)
        button.setAccessibleName(tooltip)
        button.clicked.connect(callback)
        return button

    def _mode_button(self, text: str, mode: str) -> QToolButton:
        button = QToolButton()
        button.setText(text)
        button.setToolTip(f"Show the {text.lower()}")
        button.setAccessibleName(f"Show the {text.lower()}")
        button.setCheckable(True)
        button.clicked.connect(lambda: self.mode_requested.emit(mode))
        return button

    def select_mode(self, mode: str) -> None:
        """Synchronize the projection switch with the effective map mode."""

        button = self.globe_button if mode == "globe" else self.map_2d_button
        if button is not None:
            button.setChecked(True)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._position_controls()

    def _position_controls(self) -> None:
        margin = 10
        self._navigation.adjustSize()
        self._navigation.move(margin, margin)
        self._navigation.raise_()
        if self._view_switch is not None:
            self._view_switch.adjustSize()
            self._view_switch.move(
                max(self.width() - self._view_switch.width() - margin, margin),
                margin,
            )
            self._view_switch.raise_()
