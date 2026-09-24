"""Render bundled geographic geometry into an offline globe texture."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QImage, QPainter, QPainterPath, QPalette, QPen, QPolygonF

from .geometry import GeometryParts, split_geometry
from .map_canvas import map_theme


@dataclass(frozen=True, slots=True)
class TextureSize:
    """Pixel dimensions for one globe rendering representation."""

    width: int
    height: int


def texture_size(geometry_resolution: str, texture_scale: int = 1) -> TextureSize:
    """Return a bounded texture size for a geometry representation."""

    if texture_scale not in {1, 2}:
        raise ValueError("texture_scale must be 1 or 2")
    base = TextureSize(2880, 1440) if geometry_resolution == "high" else TextureSize(1440, 720)
    return TextureSize(base.width * texture_scale, base.height * texture_scale)


def _point(longitude: float, latitude: float, size: TextureSize) -> QPointF:
    return QPointF(
        (longitude + 180.0) * size.width / 360.0,
        (90.0 - latitude) * size.height / 180.0,
    )


def _paths(parts: GeometryParts, size: TextureSize) -> tuple[QPainterPath, QPainterPath]:
    polygons = QPainterPath()
    polygons.setFillRule(Qt.FillRule.OddEvenFill)
    for polygon in parts.polygons:
        for ring in polygon:
            if len(ring) < 3:
                continue
            polygons.addPolygon(
                QPolygonF([_point(longitude, latitude, size) for longitude, latitude in ring])
            )
            polygons.closeSubpath()

    lines = QPainterPath()
    for line in parts.lines:
        if not line:
            continue
        lines.moveTo(_point(*line[0], size))
        for position in line[1:]:
            lines.lineTo(_point(*position, size))
    return polygons, lines


def render_globe_texture(
    *,
    land: dict[str, object] | None,
    selected: dict[str, object] | None,
    marker: tuple[float, float] | None,
    geometry_resolution: str,
    palette: QPalette,
    texture_scale: int = 1,
) -> QImage:
    """Render land, a selected region, and a marker into one equirectangular image."""

    size = texture_size(geometry_resolution, texture_scale)
    theme = map_theme(palette)
    image = QImage(size.width, size.height, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(theme.ocean)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    grid_pen = QPen(theme.grid)
    grid_pen.setWidth(texture_scale)
    painter.setPen(grid_pen)
    for longitude in range(-180, 181, 30):
        x = _point(float(longitude), 0.0, size).x()
        painter.drawLine(QPointF(x, 0), QPointF(x, size.height))
    for latitude in range(-90, 91, 30):
        y = _point(0.0, float(latitude), size).y()
        painter.drawLine(QPointF(0, y), QPointF(size.width, y))

    if land is not None:
        land_path, _ = _paths(split_geometry(land), size)
        coast_pen = QPen(theme.coast)
        coast_pen.setWidthF(
            (1.2 if geometry_resolution == "high" else 0.8) * texture_scale
        )
        painter.setPen(coast_pen)
        painter.setBrush(theme.land)
        painter.drawPath(land_path)

    if selected is not None:
        selected_path, selected_lines = _paths(split_geometry(selected), size)
        selected_pen = QPen(theme.selected_border)
        selected_pen.setWidthF(
            (3.5 if geometry_resolution == "high" else 2.2) * texture_scale
        )
        painter.setPen(selected_pen)
        painter.setBrush(theme.selected_fill)
        painter.drawPath(selected_path)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(selected_lines)

    if marker is not None:
        center = _point(*marker, size)
        radius = (8.0 if geometry_resolution == "high" else 5.0) * texture_scale
        painter.setPen(QPen(theme.marker_outline, max(radius / 3, 1.0)))
        painter.setBrush(theme.marker)
        painter.drawEllipse(center, radius, radius)
        if center.x() < radius:
            painter.drawEllipse(QPointF(center.x() + size.width, center.y()), radius, radius)
        elif center.x() > size.width - radius:
            painter.drawEllipse(QPointF(center.x() - size.width, center.y()), radius, radius)

    painter.setPen(QPen(theme.frame, texture_scale))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRect(QRectF(0, 0, size.width - 1, size.height - 1))
    painter.end()
    return image
