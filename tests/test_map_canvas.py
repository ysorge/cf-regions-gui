from typing import Any

import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QColor, QContextMenuEvent, QPalette
from PySide6.QtTest import QSignalSpy

from cfregions_gui.map_canvas import WorldMap, map_theme


def test_map_theme_follows_effective_qt_palette() -> None:
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#202124"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#f1f3f4"))

    theme = map_theme(palette)

    assert theme.dark is True
    assert theme.ocean.name() == "#172830"
    assert theme.land.name() == "#343d36"


def test_polygon_holes_are_not_filled(qtbot: Any) -> None:
    canvas = WorldMap()
    qtbot.addWidget(canvas)
    canvas.set_selected_geometry(
        {
            "type": "Polygon",
            "coordinates": [
                [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]],
                [[2, 2], [4, 2], [4, 4], [2, 4], [2, 2]],
            ],
        }
    )

    assert canvas._selected_path.contains(QPointF(8, -8))
    assert not canvas._selected_path.contains(QPointF(3, -3))


def test_center_click_selects_zero_zero(qtbot: Any) -> None:
    canvas = WorldMap()
    canvas.resize(720, 360)
    canvas.show()
    qtbot.addWidget(canvas)
    spy = QSignalSpy(canvas.point_selected)

    activation_spy = QSignalSpy(canvas.point_activated)

    qtbot.mouseClick(
        canvas,
        Qt.MouseButton.LeftButton,
        pos=QPoint(canvas.width() // 2, canvas.height() // 2),
    )

    assert spy.count() == 1
    assert activation_spy.count() == 0
    longitude, latitude = spy.at(0)
    assert longitude == pytest.approx(0.0)
    assert latitude == pytest.approx(0.0)


def test_center_double_click_activates_zero_zero(qtbot: Any) -> None:
    canvas = WorldMap()
    canvas.resize(720, 360)
    canvas.show()
    qtbot.addWidget(canvas)
    spy = QSignalSpy(canvas.point_activated)

    qtbot.mouseDClick(
        canvas,
        Qt.MouseButton.LeftButton,
        pos=QPoint(canvas.width() // 2, canvas.height() // 2),
    )

    assert spy.count() == 1
    longitude, latitude = spy.at(0)
    assert longitude == pytest.approx(0.0)
    assert latitude == pytest.approx(0.0)


def test_double_click_outside_world_is_ignored(qtbot: Any) -> None:
    canvas = WorldMap()
    canvas.resize(720, 500)
    canvas.show()
    qtbot.addWidget(canvas)
    spy = QSignalSpy(canvas.point_activated)

    qtbot.mouseDClick(canvas, Qt.MouseButton.LeftButton, pos=QPoint(360, 10))

    assert spy.count() == 0


def test_pointer_move_reports_coordinate_without_lookup(qtbot: Any) -> None:
    canvas = WorldMap()
    canvas.resize(720, 360)
    canvas.show()
    qtbot.addWidget(canvas)
    hover_spy = QSignalSpy(canvas.coordinate_hovered)
    selection_spy = QSignalSpy(canvas.point_selected)

    canvas._emit_hover_coordinate(QPointF(canvas.width() // 2, canvas.height() // 2))

    assert hover_spy.count() >= 1
    longitude, latitude = hover_spy.at(hover_spy.count() - 1)
    assert longitude == pytest.approx(0.0)
    assert latitude == pytest.approx(0.0)
    assert selection_spy.count() == 0


def test_map_context_menu_reports_its_coordinate(qtbot: Any) -> None:
    canvas = WorldMap()
    canvas.resize(720, 360)
    qtbot.addWidget(canvas)
    spy = QSignalSpy(canvas.context_menu_requested)
    event = QContextMenuEvent(
        QContextMenuEvent.Reason.Mouse,
        QPoint(360, 180),
        QPoint(800, 600),
    )

    canvas.contextMenuEvent(event)

    assert spy.count() == 1
    longitude, latitude, global_position = spy.at(0)
    assert longitude == pytest.approx(0.0)
    assert latitude == pytest.approx(0.0)
    assert global_position == QPoint(800, 600)
    assert canvas._marker is None
