"""Optional native Qt Quick 3D globe widget."""

from __future__ import annotations

from importlib.resources import as_file, files
from importlib.util import find_spec
from math import isfinite

from PySide6.QtCore import (
    Property,
    QByteArray,
    QEvent,
    QObject,
    Qt,
    QTimer,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import QImage, QPalette, QSurfaceFormat
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtWidgets import QWidget

from .geometry import split_geometry
from .globe_texture import render_globe_texture


def globe_available() -> bool:
    """Return whether the optional Qt Quick 3D Python module is installed."""

    try:
        return find_spec("PySide6.QtQuick3D") is not None
    except (ImportError, ModuleNotFoundError):
        return False


def prepare_globe_surface() -> bool:
    """Request Qt Quick 3D's preferred surface format before a window exists."""

    if not globe_available():
        return False
    from PySide6.QtQuick3D import QQuick3D

    QSurfaceFormat.setDefaultFormat(QQuick3D.idealSurfaceFormat(4))
    return True


def uv_to_coordinate(u: float, v: float) -> tuple[float, float]:
    """Convert the picked sphere UV position to OGC:CRS84 coordinates."""

    longitude = (float(u) * 360.0) % 360.0 - 180.0
    latitude = min(max(float(v) * 180.0 - 90.0, -90.0), 90.0)
    return longitude, latitude


def texture_scale_for_camera(camera_distance: float, current_scale: int) -> int:
    """Choose a bounded texture tier with hysteresis around the zoom threshold."""

    if current_scale == 1:
        return 2 if camera_distance <= 205.0 else 1
    return 1 if camera_distance >= 235.0 else 2


def geometry_resolution_from_feature(feature: dict[str, object] | None) -> str | None:
    """Return the declared geometry resolution from a feature, if valid."""

    if feature is None:
        return None
    properties = feature.get("properties")
    if not isinstance(properties, dict):
        return None
    resolution = properties.get("geometry_resolution")
    if resolution in {"low", "high"}:
        return str(resolution)
    return None


def globe_geometry_resolution(
    land: dict[str, object] | None,
    selected: dict[str, object] | None,
) -> str:
    """Choose globe texture resolution, preferring the selected geometry."""

    return (
        geometry_resolution_from_feature(selected)
        or geometry_resolution_from_feature(land)
        or "low"
    )


class GlobeController(QObject):
    """Small QML bridge containing globe state and interaction logic."""

    point_selected = Signal(float, float)
    point_activated = Signal(float, float)
    coordinate_hovered = Signal(float, float)
    pointer_left = Signal()
    rotation_changed = Signal()
    camera_distance_changed = Signal()
    dark_changed = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._rotation_x = 0.0
        self._rotation_y = 0.0
        self._camera_distance = 280.0
        self._dark = False

    @Property(float, notify=rotation_changed)
    def rotation_x(self) -> float:
        return self._rotation_x

    @Property(float, notify=rotation_changed)
    def rotation_y(self) -> float:
        return self._rotation_y

    @Property(float, notify=camera_distance_changed)
    def camera_distance(self) -> float:
        return self._camera_distance

    def current_camera_distance(self) -> float:
        """Return the camera distance for native-side rendering decisions."""

        return self._camera_distance

    @Property(bool, notify=dark_changed)
    def dark(self) -> bool:
        return self._dark

    def set_dark(self, dark: bool) -> None:
        if self._dark != dark:
            self._dark = dark
            self.dark_changed.emit()

    @Slot(float, float)
    def rotate(self, horizontal: float, vertical: float) -> None:
        self._rotation_y = (self._rotation_y + horizontal * 0.35) % 360.0
        self._rotation_x = min(max(self._rotation_x + vertical * 0.25, -85.0), 85.0)
        self.rotation_changed.emit()

    @Slot(float)
    def zoom_steps(self, steps: float) -> None:
        factor = 0.88 ** float(steps)
        self._camera_distance = min(max(self._camera_distance * factor, 125.0), 620.0)
        self.camera_distance_changed.emit()

    @Slot(float, float)
    def select_uv(self, u: float, v: float) -> None:
        longitude, latitude = uv_to_coordinate(u, v)
        if isfinite(longitude) and isfinite(latitude):
            self.point_selected.emit(longitude, latitude)

    @Slot(float, float)
    def activate_uv(self, u: float, v: float) -> None:
        longitude, latitude = uv_to_coordinate(u, v)
        if isfinite(longitude) and isfinite(latitude):
            self.point_activated.emit(longitude, latitude)

    @Slot(float, float)
    def hover_uv(self, u: float, v: float) -> None:
        longitude, latitude = uv_to_coordinate(u, v)
        if isfinite(longitude) and isfinite(latitude):
            self.coordinate_hovered.emit(longitude, latitude)

    @Slot()
    def clear_hover(self) -> None:
        self.pointer_left.emit()

    def reset_view(self) -> None:
        self._rotation_x = 0.0
        self._rotation_y = 0.0
        self._camera_distance = 280.0
        self.rotation_changed.emit()
        self.camera_distance_changed.emit()

    def fit_bounds(self, bounds: tuple[float, float, float, float] | None) -> None:
        if bounds is None:
            return
        west, south, east, north = bounds
        longitude = (west + east) / 2.0
        latitude = (south + north) / 2.0
        span = max(east - west, north - south, 4.0)
        self._rotation_x = latitude
        self._rotation_y = -longitude
        self._camera_distance = min(max(190.0 + span * 0.9, 190.0), 390.0)
        self.rotation_changed.emit()
        self.camera_distance_changed.emit()


class GlobeWidget(QQuickWidget):
    """A native, offline 3D globe backed by Qt Quick 3D."""

    point_selected = Signal(float, float)
    point_activated = Signal(float, float)
    coordinate_hovered = Signal(float, float)
    pointer_left = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        if not globe_available():
            raise RuntimeError("Install cf-regions-gui[globe] to enable the 3D globe.")
        super().__init__(parent)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.setMinimumSize(500, 360)
        self.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
        self.setClearColor(Qt.GlobalColor.transparent)
        from PySide6.QtQuick3D import QQuick3DTextureData

        self._texture_data = QQuick3DTextureData()
        self._texture_data.setFormat(QQuick3DTextureData.Format.RGBA8)
        self._texture_data.setHasTransparency(False)
        self._controller = GlobeController(self)
        self._controller.point_selected.connect(self._point_selected)
        self._controller.point_activated.connect(self._point_activated)
        self._controller.coordinate_hovered.connect(self.coordinate_hovered)
        self._controller.pointer_left.connect(self.pointer_left)
        self.rootContext().setContextProperty("controller", self._controller)
        self.rootContext().setContextProperty("globeTextureData", self._texture_data)
        self._land: dict[str, object] | None = None
        self._selected: dict[str, object] | None = None
        self._marker: tuple[float, float] | None = None
        self._texture_scale = 1
        self._texture_timer = QTimer(self)
        self._texture_timer.setInterval(220)
        self._texture_timer.setSingleShot(True)
        self._texture_timer.timeout.connect(self._adapt_texture_resolution)
        self._controller.camera_distance_changed.connect(self._schedule_texture_adaptation)

        resource = files("cfregions_gui").joinpath("globe.qml")
        with as_file(resource) as qml_path:
            self.setSource(QUrl.fromLocalFile(str(qml_path)))
        if self.status() == QQuickWidget.Status.Error:
            details = "; ".join(error.description() for error in self.errors())
            raise RuntimeError(details or "Qt Quick 3D could not initialize.")
        self._update_texture()

    def _point_selected(self, longitude: float, latitude: float) -> None:
        self.set_marker(longitude, latitude)
        self.point_selected.emit(longitude, latitude)

    def _point_activated(self, longitude: float, latitude: float) -> None:
        self.set_marker(longitude, latitude)
        self.point_activated.emit(longitude, latitude)

    def _update_texture(self) -> None:
        self._controller.set_dark(self._is_dark())
        image = render_globe_texture(
            land=self._land,
            selected=self._selected,
            marker=self._marker,
            geometry_resolution=globe_geometry_resolution(self._land, self._selected),
            palette=self.palette(),
            texture_scale=self._texture_scale,
        )
        image = image.convertToFormat(QImage.Format.Format_RGBA8888)
        self._texture_data.setSize(image.size())
        self._texture_data.setTextureData(QByteArray(bytes(image.constBits())))
        self._texture_data.markAllDirty()

    def _schedule_texture_adaptation(self) -> None:
        desired_scale = texture_scale_for_camera(
            self._controller.current_camera_distance(),
            self._texture_scale,
        )
        if desired_scale == self._texture_scale:
            self._texture_timer.stop()
        else:
            self._texture_timer.start()

    def _adapt_texture_resolution(self) -> None:
        desired_scale = texture_scale_for_camera(
            self._controller.current_camera_distance(),
            self._texture_scale,
        )
        if desired_scale != self._texture_scale:
            self._texture_scale = desired_scale
            self._update_texture()

    def _is_dark(self) -> bool:
        background = self.palette().color(QPalette.ColorRole.Window)
        foreground = self.palette().color(QPalette.ColorRole.WindowText)
        return background.lightnessF() < foreground.lightnessF()

    def set_land(self, feature: dict[str, object]) -> None:
        self._land = feature
        self._update_texture()

    def set_selected_geometry(
        self,
        feature: dict[str, object],
        *,
        clear_marker: bool = False,
    ) -> None:
        self._selected = feature
        if clear_marker:
            self._marker = None
        self._update_texture()
        self.fit_selected()

    def clear_selected_geometry(self) -> None:
        self._selected = None
        self._update_texture()

    def set_marker(self, longitude: float, latitude: float) -> None:
        self._marker = (longitude, latitude)
        self._update_texture()

    def clear_marker(self) -> None:
        self._marker = None
        self._update_texture()

    def reset_view(self) -> None:
        self._controller.reset_view()

    def zoom_in(self) -> None:
        self._controller.zoom_steps(1.0)

    def zoom_out(self) -> None:
        self._controller.zoom_steps(-1.0)

    def fit_selected(self) -> None:
        bounds = split_geometry(self._selected).bounds if self._selected is not None else None
        self._controller.fit_bounds(bounds)

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() in {
            QEvent.Type.ApplicationPaletteChange,
            QEvent.Type.PaletteChange,
            QEvent.Type.ThemeChange,
        }:
            self._update_texture()
