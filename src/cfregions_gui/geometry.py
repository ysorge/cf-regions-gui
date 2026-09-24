"""Presentation-neutral helpers for reading GeoJSON geometry."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from itertools import chain
from typing import Any

Position = tuple[float, float]
Ring = tuple[Position, ...]
Polygon = tuple[Ring, ...]
Line = tuple[Position, ...]


@dataclass(frozen=True, slots=True)
class GeometryParts:
    """GeoJSON geometry split into polygon rings and lines."""

    polygons: tuple[Polygon, ...]
    lines: tuple[Line, ...]

    @property
    def is_empty(self) -> bool:
        return not self.polygons and not self.lines

    @property
    def bounds(self) -> tuple[float, float, float, float] | None:
        sequences: Iterable[Sequence[Position]] = chain(
            self.lines,
            chain.from_iterable(self.polygons),
        )
        iterator = iter(chain.from_iterable(sequences))
        try:
            first = next(iterator)
        except StopIteration:
            return None
        west = east = first[0]
        south = north = first[1]
        for longitude, latitude in iterator:
            west = min(west, longitude)
            east = max(east, longitude)
            south = min(south, latitude)
            north = max(north, latitude)
        return west, south, east, north


def _positions(values: Sequence[Sequence[float]]) -> Ring:
    return tuple((float(position[0]), float(position[1])) for position in values)


def _collect_parts(
    geometry: dict[str, Any],
    polygons: list[Polygon],
    lines: list[Line],
) -> None:
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates", ())
    if geometry_type == "Polygon":
        polygons.append(tuple(_positions(ring) for ring in coordinates))
    elif geometry_type == "MultiPolygon":
        for polygon in coordinates:
            polygons.append(tuple(_positions(ring) for ring in polygon))
    elif geometry_type == "LineString":
        lines.append(_positions(coordinates))
    elif geometry_type == "MultiLineString":
        for line in coordinates:
            lines.append(_positions(line))
    elif geometry_type == "GeometryCollection":
        for member in geometry.get("geometries", ()):
            _collect_parts(member, polygons, lines)


def split_geometry(feature_or_geometry: dict[str, Any]) -> GeometryParts:
    """Split a GeoJSON Feature or geometry into immutable drawing primitives."""

    geometry = (
        feature_or_geometry.get("geometry", {})
        if feature_or_geometry.get("type") == "Feature"
        else feature_or_geometry
    )
    polygons: list[Polygon] = []
    lines: list[Line] = []
    _collect_parts(geometry, polygons, lines)
    return GeometryParts(tuple(polygons), tuple(lines))
