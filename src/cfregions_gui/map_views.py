"""Shared facade for the always-available map and optional offline globe."""

from __future__ import annotations

from PySide6.QtCore import QPoint, Signal
from PySide6.QtWidgets import QStackedWidget, QWidget

from .globe import GlobeWidget, globe_available
from .map_canvas import WorldMap


class MapViews(QStackedWidget):
    """Keep 2D and optional 3D views synchronized behind one small interface."""

    point_selected = Signal(float, float)
    point_activated = Signal(float, float)
    coordinate_hovered = Signal(float, float)
    pointer_left = Signal()
    context_menu_requested = Signal(float, float, QPoint)
    globe_failed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._planar = WorldMap()
        self.addWidget(self._planar)
        self._planar.point_selected.connect(self._relay_point)
        self._planar.point_activated.connect(self._relay_activation)
        self._planar.coordinate_hovered.connect(self.coordinate_hovered)
        self._planar.pointer_left.connect(self.pointer_left)
        self._planar.context_menu_requested.connect(self.context_menu_requested)
        self._globe: GlobeWidget | None = None
        self._globe_supported = globe_available()
        self._land: dict[str, object] | None = None
        self._selected: dict[str, object] | None = None
        self._marker: tuple[float, float] | None = None

    @property
    def has_globe(self) -> bool:
        return self._globe_supported

    def _relay_point(self, longitude: float, latitude: float) -> None:
        self.set_marker(longitude, latitude)
        self.point_selected.emit(longitude, latitude)

    def _relay_activation(self, longitude: float, latitude: float) -> None:
        self.set_marker(longitude, latitude)
        self.point_activated.emit(longitude, latitude)

    def _ensure_globe(self) -> GlobeWidget | None:
        if self._globe is not None:
            return self._globe
        if not self._globe_supported:
            return None
        try:
            globe = GlobeWidget()
        except RuntimeError as error:
            self._globe_supported = False
            self.globe_failed.emit(str(error))
            return None
        globe.point_selected.connect(self._relay_point)
        globe.point_activated.connect(self._relay_activation)
        globe.coordinate_hovered.connect(self.coordinate_hovered)
        globe.pointer_left.connect(self.pointer_left)
        self._globe = globe
        self.addWidget(globe)
        if self._land is not None:
            globe.set_land(self._land)
        if self._selected is not None:
            globe.set_selected_geometry(self._selected)
        if self._marker is not None:
            globe.set_marker(*self._marker)
        return globe

    def set_mode(self, mode: str) -> bool:
        """Show the requested view, returning whether it is available."""

        if mode == "2d":
            self.setCurrentWidget(self._planar)
            return True
        if mode != "globe":
            raise ValueError(f"Unknown map mode: {mode}")
        globe = self._ensure_globe()
        if globe is None:
            return False
        self.setCurrentWidget(globe)
        return True

    def set_land(self, feature: dict[str, object]) -> None:
        self._land = feature
        self._planar.set_land(feature)
        if self._globe is not None:
            self._globe.set_land(feature)

    def set_selected_geometry(
        self,
        feature: dict[str, object],
        *,
        clear_marker: bool = False,
    ) -> None:
        self._selected = feature
        if clear_marker:
            self._marker = None
        self._planar.set_selected_geometry(feature, clear_marker=clear_marker)
        if self._globe is not None:
            self._globe.set_selected_geometry(feature, clear_marker=clear_marker)

    def clear_selected_geometry(self) -> None:
        self._selected = None
        self._planar.clear_selected_geometry()
        if self._globe is not None:
            self._globe.clear_selected_geometry()

    def set_marker(self, longitude: float, latitude: float) -> None:
        self._marker = (longitude, latitude)
        self._planar.set_marker(longitude, latitude)
        if self._globe is not None:
            self._globe.set_marker(longitude, latitude)

    def clear_marker(self) -> None:
        self._marker = None
        self._planar.clear_marker()
        if self._globe is not None:
            self._globe.clear_marker()

    def reset_view(self) -> None:
        current = self.currentWidget()
        if isinstance(current, GlobeWidget):
            current.reset_view()
        else:
            self._planar.reset_view()

    def fit_selected(self) -> None:
        current = self.currentWidget()
        if isinstance(current, GlobeWidget):
            current.fit_selected()
        else:
            self._planar.fit_selected()

    def zoom_in(self) -> None:
        current = self.currentWidget()
        if isinstance(current, GlobeWidget):
            current.zoom_in()
        else:
            self._planar.zoom_in()

    def zoom_out(self) -> None:
        current = self.currentWidget()
        if isinstance(current, GlobeWidget):
            current.zoom_out()
        else:
            self._planar.zoom_out()
