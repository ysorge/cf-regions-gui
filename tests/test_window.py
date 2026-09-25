from typing import Any

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox, QToolBar

from cfregions_gui.session import RegionSession
from cfregions_gui.window import MainWindow, coordinate_paste_options


@pytest.mark.parametrize(
    ("clipboard_text", "expected"),
    [
        (
            "13.405, 52.52",
            [
                ("Paste lon/lat", 13.405, 52.52),
                ("Paste lat/lon", 52.52, 13.405),
            ],
        ),
        ("100, 50", [("Paste lon/lat", 100.0, 50.0)]),
        ("50, 100", [("Paste lat/lon", 100.0, 50.0)]),
        ("1", []),
        ("1, 2, 3", []),
        ("north, sea", []),
        ("nan, 1", []),
        ("181, 91", []),
    ],
)
def test_coordinate_paste_options_validate_both_orders(
    clipboard_text: str,
    expected: list[tuple[str, float, float]],
) -> None:
    assert coordinate_paste_options(clipboard_text) == expected


def test_window_loads_offline_dataset(qtbot: Any) -> None:
    window = MainWindow(RegionSession(cf_version="5"))
    qtbot.addWidget(window)

    assert window.windowTitle() == "CF Regions"
    assert not any(
        label.text() == "CF Standardized Regions"
        for label in window.findChildren(QLabel)
    )
    assert window._region.count() == 74
    assert window._profile.count() == 1
    assert window._profile_version.currentText() == "2026.09.1"
    assert window._profile.isHidden()
    assert window._profile_version.isHidden()
    assert window._resolution.count() == 2
    assert window._results.horizontalHeaderItem(0).text() == "Region"
    assert window._results.horizontalHeaderItem(1).text() == "How matched"
    assert "Offline vector map" in window.statusBar().currentMessage()
    assert window._map.currentIndex() == 0
    assert window._details_group.isHidden()
    assert window._map_viewport.world_button.toolTip() == "Reset to the world view"
    assert window._map_viewport.fit_button.toolTip() == "Fit the selected region"
    assert window._map_viewport.zoom_in_button.text() == "+"
    assert window._map_viewport.zoom_out_button.text() == "-"
    initial_zoom = window._map._planar._zoom
    window._map_viewport.zoom_in_button.click()
    assert window._map._planar._zoom > initial_zoom
    window._map_viewport.world_button.click()
    assert window._map._planar._zoom == 1.0
    if window._map.has_globe:
        assert window._map_viewport.map_2d_button is not None
        assert window._map_viewport.map_2d_button.isChecked()
        assert window._map_viewport.globe_button is not None

    window._show_region("north_sea")

    assert not window._details_group.isHidden()
    details = window._details.toPlainText()
    assert "Mapping:" in details
    assert "SeaVoX" in details


def test_selected_region_details_can_collapse_expand_and_resize(qtbot: Any) -> None:
    window = MainWindow(RegionSession(cf_version="5"))
    qtbot.addWidget(window)
    window.resize(1180, 760)
    window.show()
    window._show_region("north_sea")
    qtbot.wait(20)

    assert window._map_splitter.orientation() == Qt.Orientation.Vertical
    assert window._details_group.is_expanded
    assert not window._details.isHidden()
    assert (
        window._details_group.toggle_button.toolTip()
        == "Collapse selected region details"
    )
    total_height = sum(window._map_splitter.sizes())
    window._map_splitter.setSizes([total_height - 240, 240])
    resized_height = window._map_splitter.sizes()[1]
    assert resized_height >= 200

    window._details_group.toggle_button.click()

    assert not window._details_group.isHidden()
    assert not window._details_group.is_expanded
    assert window._details.isHidden()
    assert (
        window._details_group.toggle_button.toolTip()
        == "Expand selected region details"
    )

    window._details_group.toggle_button.click()

    assert window._details_group.is_expanded
    assert not window._details.isHidden()
    assert window._map_splitter.sizes()[1] == pytest.approx(resized_height, abs=1)

    total_height = sum(window._map_splitter.sizes())
    collapsed_height = window._details_group.collapsed_height
    window._map_splitter.moveSplitter(total_height - collapsed_height, 1)

    assert not window._details_group.is_expanded
    assert window._details.isHidden()
    assert window._map_splitter.sizes()[1] == pytest.approx(collapsed_height, abs=1)

    window._map_splitter.moveSplitter(total_height - 100, 1)

    assert window._details_group.is_expanded
    assert not window._details.isHidden()
    assert window._map_splitter.sizes()[1] == pytest.approx(resized_height, abs=1)


def test_sidebar_scrolls_and_lookup_results_use_table_rows(qtbot: Any) -> None:
    window = MainWindow(RegionSession(cf_version="5"))
    qtbot.addWidget(window)
    window.resize(880, 580)
    window.show()
    qtbot.wait(20)

    assert window.findChildren(QToolBar) == []
    assert window._map_viewport._navigation.geometry().top() >= 0
    assert window._map_viewport._navigation.geometry().left() >= 0
    assert window._map_viewport._navigation.geometry().bottom() < window._map_viewport.height()
    assert (
        window._sidebar_scroll.verticalScrollBarPolicy()
        == Qt.ScrollBarPolicy.ScrollBarAsNeeded
    )
    sidebar = window._sidebar_scroll.widget()
    assert sidebar is not None
    sidebar.setMinimumHeight(window._sidebar_scroll.viewport().height() + 100)
    qtbot.waitUntil(
        lambda: window._sidebar_scroll.verticalScrollBar().maximum() > 0
    )
    assert window._longitude.height() >= window._longitude.minimumSizeHint().height()
    assert window._latitude.height() >= window._latitude.minimumSizeHint().height()
    assert window._longitude.geometry().bottom() < window._latitude.geometry().top()

    window._longitude.setValue(13.405)
    window._latitude.setValue(52.52)
    window._lookup()

    assert window._results.rowCount() > 0
    for row in range(window._results.rowCount()):
        assert "\n" not in window._results.item(row, 0).text()
        assert window._results.item(row, 1).text() in {
            "Geometry match",
            "Hierarchy parent",
        }


def test_mapping_dialog_contains_context_removed_from_sidebar(
    qtbot: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window = MainWindow(RegionSession(cf_version="5"))
    qtbot.addWidget(window)
    captured: dict[str, str] = {}

    def capture_information(parent: object, title: str, text: str) -> object:
        del parent
        captured["title"] = title
        captured["text"] = text
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QMessageBox, "information", capture_information)
    window._show_mapping_notes()

    assert captured["title"] == "Mapping provenance and limitations"
    assert "CF standardizes region names, not boundaries" in captured["text"]
    assert "cfregions-default@2026.09.1" in captured["text"]
    assert "NASA GCMD" in captured["text"]
    assert "Region names: 74" in captured["text"]


def test_manual_region_selection_resets_point_state_and_updates_connections(
    qtbot: Any,
) -> None:
    window = MainWindow(RegionSession(cf_version="5"))
    qtbot.addWidget(window)
    window._longitude.setValue(13.405)
    window._latitude.setValue(52.52)
    window._tolerance.setValue(10.0)
    window._lookup_from_controls()
    assert window._map._marker == (13.405, 52.52)

    window._region.setCurrentText("north_sea")
    window._show_selected_region()

    assert window._longitude.value() == 0.0
    assert window._latitude.value() == 0.0
    assert window._tolerance.value() == 0.0
    assert window._map._marker is None
    assert [
        window._results.item(row, 0).text() for row in range(window._results.rowCount())
    ] == ["north_sea", "atlantic_ocean", "global_ocean", "global"]
    assert [
        window._results.item(row, 1).text() for row in range(window._results.rowCount())
    ] == ["Selected region", "Direct parent", "Hierarchy ancestor", "Hierarchy ancestor"]


def test_hover_coordinate_has_independent_status_field(qtbot: Any) -> None:
    window = MainWindow(RegionSession(cf_version="5"))
    qtbot.addWidget(window)

    window._map.coordinate_hovered.emit(13.405, 52.52)
    assert window._cursor_coordinate.text() == "Lon: 13.40500  Lat: 52.52000"

    window._map.pointer_left.emit()
    assert window._cursor_coordinate.text() == "Lon: --  Lat: --"


def test_map_click_looks_up_and_double_click_opens_first_result(qtbot: Any) -> None:
    window = MainWindow(RegionSession(cf_version="5"))
    qtbot.addWidget(window)
    window.show()
    qtbot.wait(20)
    canvas = window._map._planar
    center = QPoint(canvas.width() // 2, canvas.height() // 2)

    qtbot.mouseClick(canvas, Qt.MouseButton.LeftButton, pos=center)
    assert window._map._marker is not None
    assert window._results.rowCount() > 0
    assert window._shown_region is None

    qtbot.mouseDClick(canvas, Qt.MouseButton.LeftButton, pos=center)
    assert window._map._marker is not None
    assert window._results.rowCount() > 0
    assert window._results.currentRow() == 0
    assert window._shown_region == window._results.item(0, 0).text()
    assert not window._details_group.isHidden()


def test_context_menus_copy_coordinates_and_region_names(qtbot: Any) -> None:
    window = MainWindow(RegionSession(cf_version="5"))
    qtbot.addWidget(window)
    assert (
        window._results.contextMenuPolicy()
        == Qt.ContextMenuPolicy.CustomContextMenu
    )
    assert window._region.contextMenuPolicy() == Qt.ContextMenuPolicy.CustomContextMenu
    assert (
        window._lookup_group.contextMenuPolicy()
        == Qt.ContextMenuPolicy.CustomContextMenu
    )

    window._copy_lon_lat(12.5, -4.25)
    assert QApplication.clipboard().text() == "12.500000, -4.250000"

    window._longitude.setValue(13.405)
    window._latitude.setValue(52.52)
    window._copy_lon_lat(window._longitude.value(), window._latitude.value())
    assert QApplication.clipboard().text() == "13.405000, 52.520000"

    window._paste_lon_lat(-74.006, 40.7128)
    assert window._longitude.value() == -74.006
    assert window._latitude.value() == 40.7128

    window._region.setCurrentText("north_sea")
    window._copy_region_name(window._region.currentText())
    assert QApplication.clipboard().text() == "north_sea"

    window._lookup_from_controls()
    window._results.selectRow(0)
    first_name = window._results.item(0, 0).text()
    selected_name = window._selected_result_name()
    assert selected_name is not None
    window._copy_region_name(selected_name)
    assert QApplication.clipboard().text() == first_name

    window._copy_all_region_names()
    expected = ", ".join(
        window._results.item(row, 0).text()
        for row in range(window._results.rowCount())
    )
    assert QApplication.clipboard().text() == expected
