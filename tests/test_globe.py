from typing import Any

import pytest
from PySide6.QtCore import QObject, QPoint, Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtTest import QSignalSpy

from cfregions_gui.globe import (
    GlobeController,
    GlobeWidget,
    globe_geometry_resolution,
    geometry_resolution_from_feature,
    globe_available,
    texture_scale_for_camera,
    uv_to_coordinate,
)
from cfregions_gui.globe_texture import render_globe_texture, texture_size


def test_uv_to_coordinate_uses_longitude_latitude_order() -> None:
    assert uv_to_coordinate(0.5, 0.5) == pytest.approx((0.0, 0.0))
    assert uv_to_coordinate(0.75, 1.0) == pytest.approx((90.0, 90.0))
    assert uv_to_coordinate(0.25, 0.0) == pytest.approx((-90.0, -90.0))


def test_fit_bounds_centers_region_without_losing_globe_context() -> None:
    controller = GlobeController()

    controller.fit_bounds((-5.0, 50.0, 10.0, 60.0))

    assert controller.rotation_x == pytest.approx(55.0)
    assert controller.rotation_y == pytest.approx(-2.5)
    assert 190.0 <= controller.camera_distance < 280.0


def test_texture_scale_adapts_with_hysteresis() -> None:
    assert texture_scale_for_camera(280.0, 1) == 1
    assert texture_scale_for_camera(200.0, 1) == 2
    assert texture_scale_for_camera(220.0, 2) == 2
    assert texture_scale_for_camera(240.0, 2) == 1


def test_geometry_resolution_prefers_declared_feature_values() -> None:
    assert geometry_resolution_from_feature(None) is None
    assert geometry_resolution_from_feature({"properties": {}}) is None
    assert (
        geometry_resolution_from_feature({"properties": {"geometry_resolution": "low"}})
        == "low"
    )
    assert (
        geometry_resolution_from_feature({"properties": {"geometry_resolution": "high"}})
        == "high"
    )
    assert (
        geometry_resolution_from_feature({"properties": {"geometry_resolution": "unknown"}})
        is None
    )


def test_globe_geometry_resolution_prefers_selected_over_land() -> None:
    assert (
        globe_geometry_resolution(
            {"properties": {"geometry_resolution": "low"}},
            {"properties": {"geometry_resolution": "high"}},
        )
        == "high"
    )
    assert (
        globe_geometry_resolution({"properties": {"geometry_resolution": "low"}}, None)
        == "low"
    )
    assert globe_geometry_resolution(None, None) == "low"


def test_globe_hover_conversion_does_not_select_a_point() -> None:
    controller = GlobeController()
    hover_spy = QSignalSpy(controller.coordinate_hovered)
    selection_spy = QSignalSpy(controller.point_selected)

    controller.hover_uv(0.75, 0.75)

    assert hover_spy.count() == 1
    assert hover_spy.at(0) == pytest.approx([90.0, 45.0])
    assert selection_spy.count() == 0


def test_globe_activation_has_a_distinct_signal() -> None:
    controller = GlobeController()
    selection_spy = QSignalSpy(controller.point_selected)
    activation_spy = QSignalSpy(controller.point_activated)

    controller.activate_uv(0.75, 0.75)

    assert activation_spy.count() == 1
    assert activation_spy.at(0) == pytest.approx([90.0, 45.0])
    assert selection_spy.count() == 0


def test_globe_texture_uses_requested_detail_and_theme() -> None:
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#202124"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#f1f3f4"))
    land = {
        "type": "Feature",
        "properties": {"geometry_resolution": "low"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 0]]],
        },
    }

    image = render_globe_texture(
        land=land,
        selected=None,
        marker=(5.0, 5.0),
        geometry_resolution="low",
        palette=palette,
    )

    assert (image.width(), image.height()) == (
        texture_size("low").width,
        texture_size("low").height,
    )
    assert texture_size("high").width > image.width()
    assert texture_size("low", 2) == texture_size("high")
    assert texture_size("high", 2).width == 5760


@pytest.mark.skipif(not globe_available(), reason="optional globe extra is not installed")
def test_globe_qml_loads_when_extra_is_installed(qtbot: Any) -> None:
    globe = GlobeWidget()
    qtbot.addWidget(globe)

    assert globe.status() == QQuickWidget.Status.Ready
    assert globe.contextMenuPolicy() == Qt.ContextMenuPolicy.NoContextMenu
    root = globe.rootObject()
    assert root is not None
    texture = root.findChild(QObject, "globeTexture")
    assert texture is not None
    assert texture.property("flipV") is True
    light = root.findChild(QObject, "globeLight")
    assert light is not None
    globe._controller.set_dark(False)
    qtbot.waitUntil(lambda: float(light.property("brightness")) == pytest.approx(0.55))
    globe._controller.set_dark(True)
    qtbot.waitUntil(lambda: float(light.property("brightness")) == pytest.approx(1.2))

    globe._controller.zoom_steps(3.0)
    qtbot.waitUntil(lambda: globe._texture_scale == 2)
    assert globe._texture_data.size().width() == 2880

    globe.reset_view()
    qtbot.waitUntil(lambda: globe._texture_scale == 1)
    assert globe._texture_data.size().width() == 1440


@pytest.mark.skipif(not globe_available(), reason="optional globe extra is not installed")
def test_globe_distinguishes_drag_from_click(qtbot: Any) -> None:
    globe = GlobeWidget()
    qtbot.addWidget(globe)
    globe.resize(600, 400)
    globe.show()
    qtbot.waitExposed(globe)
    center = QPoint(globe.width() // 2, globe.height() // 2)
    root = globe.rootObject()
    assert root is not None
    mouse_area = root.findChild(QObject, "globeMouseArea")
    assert mouse_area is not None

    qtbot.mousePress(globe, Qt.MouseButton.LeftButton, pos=center)
    qtbot.mouseMove(globe, center + QPoint(30, 10))
    qtbot.mouseRelease(
        globe,
        Qt.MouseButton.LeftButton,
        pos=center + QPoint(30, 10),
    )

    assert mouse_area.property("dragged") is True

    qtbot.mousePress(globe, Qt.MouseButton.LeftButton, pos=center)
    assert mouse_area.property("dragged") is False
    qtbot.mouseRelease(globe, Qt.MouseButton.LeftButton, pos=center)
