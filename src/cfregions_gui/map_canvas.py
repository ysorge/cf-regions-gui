"""A compact, tile-free world map widget."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from PySide6.QtCore import QEvent, QPoint, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QContextMenuEvent,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
    QPolygonF,
    QResizeEvent,
    QWheelEvent,
)
from PySide6.QtWidgets import QWidget

from .geometry import GeometryParts, split_geometry


@dataclass(frozen=True, slots=True)
class MapTheme:
    """Colors for one effective Qt palette."""

    dark: bool
    outside: QColor
    ocean: QColor
    grid: QColor
    land: QColor
    coast: QColor
    selected_border: QColor
    selected_fill: QColor
    frame: QColor
    marker: QColor
    marker_outline: QColor


def map_theme(palette: QPalette) -> MapTheme:
    """Return map colors matching the effective widget palette."""

    background = palette.color(QPalette.ColorRole.Window)
    foreground = palette.color(QPalette.ColorRole.WindowText)
    dark = background.lightnessF() < foreground.lightnessF()
    if dark:
        return MapTheme(
            dark=True,
            outside=QColor("#181a1d"),
            ocean=QColor("#172830"),
            grid=QColor("#2c4651"),
            land=QColor("#343d36"),
            coast=QColor("#77837a"),
            selected_border=QColor("#61b0ff"),
            selected_fill=QColor(64, 151, 235, 118),
            frame=QColor("#5a6b72"),
            marker=QColor("#ff6565"),
            marker_outline=QColor("#ffb0b0"),
        )
    return MapTheme(
        dark=False,
        outside=QColor("#f2f3f4"),
        ocean=QColor("#e8f1f5"),
        grid=QColor("#c9d8de"),
        land=QColor("#d6ddd2"),
        coast=QColor("#8f9b91"),
        selected_border=QColor("#155ba6"),
        selected_fill=QColor(43, 127, 210, 92),
        frame=QColor("#8aa0a9"),
        marker=QColor("#d83939"),
        marker_outline=QColor("#a51f1f"),
    )


class WorldMap(QWidget):
    """Interactive equirectangular world map rendered entirely by Qt."""

    point_selected = Signal(float, float)
    point_activated = Signal(float, float)
    coordinate_hovered = Signal(float, float)
    pointer_left = Signal()
    context_menu_requested = Signal(float, float, QPoint)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(500, 360)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.CrossCursor)

        self._zoom = 1.0
        self._center_longitude = 0.0
        self._center_latitude = 0.0
        self._land_path = QPainterPath()
        self._selected_path = QPainterPath()
        self._selected_lines = QPainterPath()
        self._selected_bounds: tuple[float, float, float, float] | None = None
        self._marker: tuple[float, float] | None = None
        self._press_position: QPoint | None = None
        self._press_center: tuple[float, float] | None = None
        self._dragged = False

    @staticmethod
    def _path(parts: GeometryParts) -> tuple[QPainterPath, QPainterPath]:
        polygon_path = QPainterPath()
        polygon_path.setFillRule(Qt.FillRule.OddEvenFill)
        for polygon in parts.polygons:
            for ring in polygon:
                if len(ring) < 3:
                    continue
                points = QPolygonF(
                    [QPointF(longitude, -latitude) for longitude, latitude in ring]
                )
                polygon_path.addPolygon(points)
                polygon_path.closeSubpath()

        line_path = QPainterPath()
        for line in parts.lines:
            if not line:
                continue
            line_path.moveTo(line[0][0], -line[0][1])
            for longitude, latitude in line[1:]:
                line_path.lineTo(longitude, -latitude)
        return polygon_path, line_path

    def set_land(self, feature: dict[str, object]) -> None:
        """Set the offline vector land background."""

        self._land_path, _ = self._path(split_geometry(feature))
        self.update()

    def set_selected_geometry(
        self,
        feature: dict[str, object],
        *,
        clear_marker: bool = False,
    ) -> None:
        """Draw and fit one selected region."""

        parts = split_geometry(feature)
        self._selected_path, self._selected_lines = self._path(parts)
        self._selected_bounds = parts.bounds
        if clear_marker:
            self._marker = None
        self.fit_selected()

    def clear_selected_geometry(self) -> None:
        self._selected_path = QPainterPath()
        self._selected_lines = QPainterPath()
        self._selected_bounds = None
        self.update()

    def set_marker(self, longitude: float, latitude: float) -> None:
        self._marker = (longitude, latitude)
        self.update()

    def clear_marker(self) -> None:
        self._marker = None
        self.update()

    def reset_view(self) -> None:
        self._zoom = 1.0
        self._center_longitude = 0.0
        self._center_latitude = 0.0
        self.update()

    def zoom_in(self) -> None:
        self._set_zoom(self._zoom * 1.5, QPointF(self.width() / 2, self.height() / 2))

    def zoom_out(self) -> None:
        self._set_zoom(self._zoom / 1.5, QPointF(self.width() / 2, self.height() / 2))

    def fit_selected(self) -> None:
        bounds = self._selected_bounds
        if bounds is None or self.width() <= 0 or self.height() <= 0:
            self.update()
            return
        west, south, east, north = bounds
        width = max(east - west, 1.0)
        height = max(north - south, 1.0)
        usable_width = max(self.width() - 100, 1)
        usable_height = max(self.height() - 100, 1)
        desired_scale = min(usable_width / width, usable_height / height)
        self._zoom = min(max(desired_scale / self._base_scale(), 1.0), 64.0)
        self._center_longitude = (west + east) / 2
        self._center_latitude = (south + north) / 2
        self._clamp_center()
        self.update()

    def _base_scale(self) -> float:
        return max(min(self.width() / 360.0, self.height() / 180.0), 0.01)

    def _scale(self) -> float:
        return self._base_scale() * self._zoom

    def _screen_to_coordinate(self, position: QPointF) -> tuple[float, float]:
        scale = self._scale()
        longitude = self._center_longitude + (position.x() - self.width() / 2) / scale
        latitude = self._center_latitude - (position.y() - self.height() / 2) / scale
        return longitude, latitude

    def _coordinate_to_screen(self, longitude: float, latitude: float) -> QPointF:
        scale = self._scale()
        return QPointF(
            self.width() / 2 + (longitude - self._center_longitude) * scale,
            self.height() / 2 - (latitude - self._center_latitude) * scale,
        )

    def _clamp_center(self) -> None:
        scale = self._scale()
        half_longitude = self.width() / (2 * scale)
        half_latitude = self.height() / (2 * scale)
        max_longitude = max(180.0 - half_longitude, 0.0)
        max_latitude = max(90.0 - half_latitude, 0.0)
        self._center_longitude = min(max(self._center_longitude, -max_longitude), max_longitude)
        self._center_latitude = min(max(self._center_latitude, -max_latitude), max_latitude)

    def _set_zoom(self, zoom: float, anchor: QPointF) -> None:
        before = self._screen_to_coordinate(anchor)
        self._zoom = min(max(zoom, 1.0), 64.0)
        after = self._screen_to_coordinate(anchor)
        self._center_longitude += before[0] - after[0]
        self._center_latitude += before[1] - after[1]
        self._clamp_center()
        self.update()

    def paintEvent(self, event: object) -> None:
        del event
        theme = map_theme(self.palette())
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), theme.outside)

        painter.translate(self.width() / 2, self.height() / 2)
        painter.scale(self._scale(), self._scale())
        painter.translate(-self._center_longitude, self._center_latitude)
        painter.fillRect(QRectF(-180, -90, 360, 180), theme.ocean)

        grid_pen = QPen(theme.grid)
        grid_pen.setCosmetic(True)
        painter.setPen(grid_pen)
        for longitude in range(-180, 181, 30):
            painter.drawLine(QPointF(longitude, -90), QPointF(longitude, 90))
        for latitude in range(-90, 91, 30):
            painter.drawLine(QPointF(-180, -latitude), QPointF(180, -latitude))
        painter.drawRect(QRectF(-180, -90, 360, 180))

        coast_pen = QPen(theme.coast)
        coast_pen.setWidthF(0.8)
        coast_pen.setCosmetic(True)
        painter.setPen(coast_pen)
        painter.setBrush(theme.land)
        painter.drawPath(self._land_path)

        selected_pen = QPen(theme.selected_border)
        selected_pen.setWidthF(2.2)
        selected_pen.setCosmetic(True)
        painter.setPen(selected_pen)
        painter.setBrush(theme.selected_fill)
        painter.drawPath(self._selected_path)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(self._selected_lines)

        painter.resetTransform()
        border_pen = QPen(theme.frame)
        border_pen.setWidth(1)
        painter.setPen(border_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

        if self._marker is not None:
            point = self._coordinate_to_screen(*self._marker)
            painter.setPen(QPen(theme.outside, 2))
            painter.setBrush(theme.marker)
            painter.drawEllipse(point, 7, 7)
            painter.setPen(QPen(theme.marker_outline, 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(point, 9, 9)

    def wheelEvent(self, event: QWheelEvent) -> None:
        steps = event.angleDelta().y() / 120
        if steps:
            self._set_zoom(self._zoom * (1.25**steps), event.position())
        event.accept()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_position = event.position().toPoint()
            self._press_center = (self._center_longitude, self._center_latitude)
            self._dragged = False
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._press_position is None or self._press_center is None:
            self._emit_hover_coordinate(event.position())
            return
        delta = event.position().toPoint() - self._press_position
        if delta.manhattanLength() > 3:
            self._dragged = True
        scale = self._scale()
        self._center_longitude = self._press_center[0] - delta.x() / scale
        self._center_latitude = self._press_center[1] + delta.y() / scale
        self._clamp_center()
        self._emit_hover_coordinate(event.position())
        self.update()
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton or self._press_position is None:
            return
        self.setCursor(Qt.CursorShape.CrossCursor)
        if not self._dragged:
            coordinate = self._valid_coordinate(event.position())
            if coordinate is not None:
                self.set_marker(*coordinate)
                self.point_selected.emit(*coordinate)
        self._press_position = None
        self._press_center = None
        event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        coordinate = self._valid_coordinate(event.position())
        if coordinate is not None:
            self.set_marker(*coordinate)
            self.point_activated.emit(*coordinate)
        event.accept()

    def leaveEvent(self, event: QEvent) -> None:
        self.pointer_left.emit()
        super().leaveEvent(event)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        coordinate = self._valid_coordinate(QPointF(event.pos()))
        if coordinate is None:
            event.ignore()
            return
        self.context_menu_requested.emit(*coordinate, event.globalPos())
        event.accept()

    def _valid_coordinate(self, position: QPointF) -> tuple[float, float] | None:
        longitude, latitude = self._screen_to_coordinate(position)
        if (
            isfinite(longitude)
            and isfinite(latitude)
            and -180.0 <= longitude <= 180.0
            and -90.0 <= latitude <= 90.0
        ):
            return longitude, latitude
        return None

    def _emit_hover_coordinate(self, position: QPointF) -> None:
        coordinate = self._valid_coordinate(position)
        if coordinate is None:
            self.pointer_left.emit()
        else:
            self.coordinate_hovered.emit(*coordinate)

    def resizeEvent(self, event: QResizeEvent) -> None:
        self._clamp_center()
        super().resizeEvent(event)

    def changeEvent(self, event: QEvent) -> None:
        """Repaint when the operating-system theme changes at runtime."""

        super().changeEvent(event)
        if event.type() in {
            QEvent.Type.ApplicationPaletteChange,
            QEvent.Type.PaletteChange,
            QEvent.Type.ThemeChange,
        }:
            self.update()
