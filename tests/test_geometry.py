from cfregions_gui.geometry import split_geometry


def test_split_multipolygon_preserves_rings_and_bounds() -> None:
    parts = split_geometry(
        {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [[0, 0], [4, 0], [4, 4], [0, 0]],
                    [[1, 1], [2, 1], [1, 2], [1, 1]],
                ],
                [[[10, -2], [12, -2], [10, 1], [10, -2]]],
            ],
        }
    )

    assert len(parts.polygons) == 2
    assert len(parts.polygons[0]) == 2
    assert parts.lines == ()
    assert parts.bounds == (0.0, -2.0, 12.0, 4.0)


def test_split_feature_geometry_collection() -> None:
    parts = split_geometry(
        {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "GeometryCollection",
                "geometries": [
                    {"type": "LineString", "coordinates": [[-2, 3], [4, 5]]},
                    {
                        "type": "Polygon",
                        "coordinates": [[[0, 0], [1, 0], [0, 1], [0, 0]]],
                    },
                ],
            },
        }
    )

    assert len(parts.polygons) == 1
    assert parts.lines == (((-2.0, 3.0), (4.0, 5.0)),)
    assert parts.bounds == (-2.0, 0.0, 4.0, 5.0)
