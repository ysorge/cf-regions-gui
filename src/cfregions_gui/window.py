"""Main desktop window."""

from __future__ import annotations

from html import escape
from math import isfinite

from cfregions import Region, SpatialInterpretationProfile
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHeaderView,
    QLabel,
    QLayout,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from .collapsible_panel import CollapsiblePanel
from .map_viewport import MapViewport
from .map_views import MapViews
from .session import RegionSession


def coordinate_paste_options(text: str) -> list[tuple[str, float, float]]:
    """Return valid lon/lat interpretations of a comma-separated number pair."""

    parts = text.split(",")
    if len(parts) != 2:
        return []
    try:
        first, second = (float(part.strip()) for part in parts)
    except ValueError:
        return []
    if not isfinite(first) or not isfinite(second):
        return []

    options = []
    if -180.0 <= first <= 180.0 and -90.0 <= second <= 90.0:
        options.append(("Paste lon/lat", first, second))
    if -90.0 <= first <= 90.0 and -180.0 <= second <= 180.0:
        options.append(("Paste lat/lon", second, first))
    return options


class MainWindow(QMainWindow):
    """Native controls around the reusable core library."""

    def __init__(self, session: RegionSession) -> None:
        super().__init__()
        self._session = session
        self.setWindowTitle("CF Regions")
        self.resize(1180, 760)
        self.setMinimumSize(880, 580)

        self._map = MapViews()
        self._map_viewport = MapViewport(self._map)
        self._profile = QComboBox()
        self._profile_version = QComboBox()
        self._profile_label = QLabel("Spatial profile")
        self._profile_version_label = QLabel("Profile version")
        self._version = QComboBox()
        self._resolution = QComboBox()
        self._longitude = self._coordinate_spin(-180.0, 180.0)
        self._latitude = self._coordinate_spin(-90.0, 90.0)
        self._tolerance = QDoubleSpinBox()
        self._tolerance.setRange(0.0, 1000.0)
        self._tolerance.setDecimals(1)
        self._tolerance.setSuffix(" km")
        self._results = QTableWidget(0, 2)
        self._results.setAlternatingRowColors(True)
        self._results.setHorizontalHeaderLabels(["Region", "How matched"])
        self._results.verticalHeader().setVisible(False)
        self._results.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._results.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._results.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._results.setShowGrid(False)
        result_header = self._results.horizontalHeader()
        result_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        result_header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._region = QComboBox()
        self._region.setEditable(True)
        self._region.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        completer = self._region.completer()
        if completer is not None:
            completer.setFilterMode(Qt.MatchFlag.MatchContains)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._details = QTextBrowser()
        self._details.setOpenExternalLinks(True)
        self._details.setMinimumHeight(90)
        self._cursor_coordinate = QLabel("Lon: --  Lat: --")
        self._cursor_coordinate.setMinimumWidth(190)
        self._cursor_coordinate.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._cursor_coordinate.setToolTip("Coordinate beneath the pointer (OGC:CRS84)")
        self._shown_region: str | None = None
        self._details_collapsing_from_splitter = False
        self._available_profiles: tuple[SpatialInterpretationProfile, ...] = ()
        self._available_cf_versions: tuple[str, ...] = ()

        self._build_layout()
        self._connect_signals()
        self._load_versions()

    @staticmethod
    def _coordinate_spin(minimum: float, maximum: float) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setDecimals(6)
        spin.setSingleStep(0.1)
        return spin

    def _build_layout(self) -> None:
        sidebar = QFrame()
        layout = QVBoxLayout(sidebar)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)

        version_form = QFormLayout()
        version_form.addRow(self._profile_label, self._profile)
        version_form.addRow(self._profile_version_label, self._profile_version)
        version_form.addRow("CF release", self._version)
        version_form.addRow("Region shape detail", self._resolution)
        layout.addLayout(version_form)
        mapping_notes = QPushButton("Mapping provenance and limitations…")
        mapping_notes.clicked.connect(self._show_mapping_notes)
        layout.addWidget(mapping_notes)

        self._lookup_group = QGroupBox("Coordinate lookup")
        lookup_layout = QFormLayout(self._lookup_group)
        lookup_layout.addRow("Longitude", self._longitude)
        lookup_layout.addRow("Latitude", self._latitude)
        lookup_layout.addRow("Section tolerance", self._tolerance)
        self._lookup_button = QPushButton("Find regions")
        self._lookup_button.setDefault(True)
        lookup_layout.addRow(self._lookup_button)
        layout.addWidget(self._lookup_group)

        layout.addWidget(QLabel("Connected region names"))
        self._results.setMinimumHeight(170)
        layout.addWidget(self._results, 1)

        region_group = QGroupBox("Show a region")
        region_layout = QVBoxLayout(region_group)
        region_layout.addWidget(self._region)
        show_button = QPushButton("Show region")
        region_layout.addWidget(show_button)
        layout.addWidget(region_group)

        self._sidebar_scroll = QScrollArea()
        self._sidebar_scroll.setFrameShape(QFrame.Shape.StyledPanel)
        self._sidebar_scroll.setWidgetResizable(True)
        self._sidebar_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._sidebar_scroll.setMinimumWidth(320)
        self._sidebar_scroll.setMaximumWidth(410)
        self._sidebar_scroll.setWidget(sidebar)

        self._details_group = CollapsiblePanel(
            "Selected region details",
            self._details,
        )
        self._details_group.hide()
        self._details_expanded_height = 180

        map_panel = QWidget()
        map_layout = QVBoxLayout(map_panel)
        map_layout.setContentsMargins(0, 0, 0, 0)
        self._map_splitter = QSplitter(Qt.Orientation.Vertical)
        self._map_splitter.setChildrenCollapsible(False)
        self._map_splitter.addWidget(self._map_viewport)
        self._map_splitter.addWidget(self._details_group)
        self._map_splitter.setStretchFactor(0, 1)
        self._map_splitter.setStretchFactor(1, 0)
        self._map_splitter.splitterMoved.connect(
            self._handle_details_splitter_moved
        )
        self._details_group.toggled.connect(self._resize_details_panel)
        map_layout.addWidget(self._map_splitter)

        splitter = QSplitter()
        splitter.addWidget(self._sidebar_scroll)
        splitter.addWidget(map_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        self.setCentralWidget(splitter)
        self.statusBar().addPermanentWidget(self._cursor_coordinate)

        self._lookup_button.clicked.connect(self._lookup_from_controls)
        show_button.clicked.connect(self._show_selected_region)

    def _handle_details_splitter_moved(self, position: int, index: int) -> None:
        del position, index
        if self._details_group.isHidden():
            return
        details_height = self._map_splitter.sizes()[1]
        collapsed_height = self._details_group.collapsed_height
        if self._details_group.is_expanded:
            if details_height <= collapsed_height + 4:
                self._details_expanded_height = max(
                    self._details_expanded_height,
                    180,
                )
                self._details_collapsing_from_splitter = True
                try:
                    self._details_group.set_expanded(False)
                finally:
                    self._details_collapsing_from_splitter = False
                return
            if details_height >= collapsed_height + self._details.minimumSizeHint().height():
                self._details_expanded_height = details_height
        elif details_height >= collapsed_height + 12:
            self._details_group.set_expanded(True)

    def _resize_details_panel(self, expanded: bool) -> None:
        if (
            not expanded
            and not self._details_collapsing_from_splitter
            and self._details_group.last_expanded_height > 0
        ):
            self._details_expanded_height = self._details_group.last_expanded_height
        total_height = sum(self._map_splitter.sizes())
        if total_height <= 0:
            return
        target_height = (
            self._details_expanded_height
            if expanded
            else self._details_group.collapsed_height
        )
        target_height = min(target_height, total_height // 2)
        self._map_splitter.setSizes(
            [max(total_height - target_height, 1), target_height]
        )

    def _set_map_mode(self, mode: str) -> None:
        self._clear_cursor_coordinate()
        if self._map.set_mode(mode):
            self._map_viewport.select_mode(mode)
            self.statusBar().showMessage(
                "Offline native 3D globe; drag to rotate, use the wheel to zoom."
                if mode == "globe"
                else "Offline native 2D map."
            )
            return
        self._map_viewport.select_mode("2d")
        self.statusBar().showMessage(
            "The optional 3D renderer could not start; continuing with the 2D map."
        )

    def _connect_signals(self) -> None:
        self._version.currentIndexChanged.connect(self._change_version)
        self._profile.currentIndexChanged.connect(self._change_profile)
        self._profile_version.currentIndexChanged.connect(self._change_profile_version)
        self._resolution.currentIndexChanged.connect(self._change_resolution)
        self._map.point_selected.connect(self._lookup_point)
        self._map.point_activated.connect(self._activate_point)
        self._map.coordinate_hovered.connect(self._show_cursor_coordinate)
        self._map.pointer_left.connect(self._clear_cursor_coordinate)
        self._map.context_menu_requested.connect(self._show_map_context_menu)
        self._map.globe_failed.connect(
            lambda message: self.statusBar().showMessage(f"3D globe unavailable: {message}")
        )
        self._map_viewport.mode_requested.connect(self._set_map_mode)
        self._results.itemActivated.connect(self._show_result)
        line_edit = self._region.lineEdit()
        if line_edit is not None:
            line_edit.returnPressed.connect(self._show_selected_region)
        self._configure_context_menus()

    def _load_versions(self) -> None:
        try:
            self._available_profiles = self._session.profiles()
            self._available_cf_versions = self._session.versions()
            info = self._session.dataset_info()
            current = info.cf_version
            self._session.profile = info.profile.id
            self._session.profile_version = info.profile.version
            self._profile.blockSignals(True)
            self._profile.clear()
            profiles_by_id: dict[str, SpatialInterpretationProfile] = {}
            for profile in self._available_profiles:
                profiles_by_id.setdefault(profile.id, profile)
            for profile_id, profile in sorted(profiles_by_id.items()):
                self._profile.addItem(profile.title, profile_id)
                index = self._profile.count() - 1
                self._profile.setItemData(index, profile.description, Qt.ItemDataRole.ToolTipRole)
            selected_profile = self._profile.findData(info.profile.id)
            self._profile.setCurrentIndex(max(selected_profile, 0))
            self._profile.blockSignals(False)
            multiple_profiles = len(profiles_by_id) > 1
            self._profile_label.setVisible(multiple_profiles)
            self._profile.setVisible(multiple_profiles)
            self._populate_profile_versions(info.profile.id, info.profile.version)
            self._populate_cf_versions(info.profile, current)
            self._reload_dataset()
        except Exception as error:
            self._show_error("Could not load CF region data", error)

    def _populate_profile_versions(self, profile_id: str, selected: str) -> None:
        self._profile_version.blockSignals(True)
        self._profile_version.clear()
        versions = sorted(
            item.version for item in self._available_profiles if item.id == profile_id
        )
        self._profile_version.addItems(versions)
        index = self._profile_version.findText(selected)
        self._profile_version.setCurrentIndex(max(index, 0))
        self._profile_version.blockSignals(False)
        multiple_versions = len(versions) > 1
        self._profile_version_label.setVisible(multiple_versions)
        self._profile_version.setVisible(multiple_versions)

    def _profile_info(
        self, profile_id: str, profile_version: str
    ) -> SpatialInterpretationProfile:
        return next(
            item
            for item in self._available_profiles
            if item.id == profile_id and item.version == profile_version
        )

    def _populate_cf_versions(
        self,
        profile: SpatialInterpretationProfile,
        selected: str,
    ) -> None:
        supported = [
            version
            for version in self._available_cf_versions
            if version in profile.cf_versions
        ]
        self._version.blockSignals(True)
        self._version.clear()
        for version in supported:
            self._version.addItem(f"CF {version}", version)
        index = self._version.findData(selected)
        self._version.setCurrentIndex(max(index, 0))
        self._version.blockSignals(False)

    def _change_profile(self) -> None:
        profile_id = self._profile.currentData()
        if not isinstance(profile_id, str):
            return
        versions = sorted(
            item.version for item in self._available_profiles if item.id == profile_id
        )
        if not versions:
            return
        selected = versions[-1]
        self._populate_profile_versions(profile_id, selected)
        try:
            profile = self._profile_info(profile_id, selected)
            cf_version = (
                self._session.cf_version
                if self._session.cf_version in profile.cf_versions
                else profile.cf_versions[-1]
            )
            self._session.set_selection(
                cf_version=cf_version,
                profile=profile_id,
                profile_version=selected,
            )
            self._populate_cf_versions(profile, cf_version)
            self._reload_dataset()
        except Exception as error:
            self._show_error("Could not change spatial profile", error)

    def _change_profile_version(self) -> None:
        profile_id = self._profile.currentData()
        profile_version = self._profile_version.currentText()
        if not isinstance(profile_id, str) or not profile_version:
            return
        try:
            profile = self._profile_info(profile_id, profile_version)
            cf_version = (
                self._session.cf_version
                if self._session.cf_version in profile.cf_versions
                else profile.cf_versions[-1]
            )
            self._session.set_selection(
                cf_version=cf_version,
                profile=profile_id,
                profile_version=profile_version,
            )
            self._populate_cf_versions(profile, cf_version)
            self._reload_dataset()
        except Exception as error:
            self._show_error("Could not change spatial profile version", error)

    def _change_version(self) -> None:
        cf_version = self._version.currentData()
        if not isinstance(cf_version, str):
            return
        try:
            self._session.set_cf_version(cf_version)
            self._reload_dataset()
        except Exception as error:
            self._show_error("Could not change CF release", error)

    def _reload_dataset(self) -> None:
        info = self._session.dataset_info()
        regions = self._session.regions()
        self._resolution.blockSignals(True)
        self._resolution.clear()
        for representation in info.geometry_representations:
            self._resolution.addItem(representation.label, representation.resolution)
            index = self._resolution.count() - 1
            self._resolution.setItemData(
                index,
                representation.description,
                Qt.ItemDataRole.ToolTipRole,
            )
        selected = self._resolution.findData(info.default_geometry_resolution)
        self._resolution.setCurrentIndex(max(selected, 0))
        self._resolution.blockSignals(False)
        self._region.clear()
        self._region.addItems([region.name for region in regions])
        self._results.setRowCount(0)
        self._details.clear()
        self._details_group.hide()
        self._shown_region = None
        self._map.clear_selected_geometry()
        available_resolutions = {
            representation.resolution for representation in info.geometry_representations
        }
        overview_resolution = (
            "low"
            if "low" in available_resolutions
            else info.default_geometry_resolution
        )
        self._map.set_land(
            self._session.shape(
                "global_land",
                geometry_resolution=overview_resolution,
            )
        )
        self.statusBar().showMessage(
            f"Loaded CF {info.cf_version} with {info.profile.id}@{info.profile.version}. "
            "Offline vector map; no network or local server."
        )

    def _geometry_resolution(self) -> str | None:
        value = self._resolution.currentData()
        return value if isinstance(value, str) else None

    def _change_resolution(self) -> None:
        resolution = self._geometry_resolution()
        if resolution is None:
            return
        try:
            if self._shown_region is not None:
                self._show_region(self._shown_region)
        except Exception as error:
            self._show_error("Could not change shape detail", error)

    def _show_mapping_notes(self) -> None:
        info = self._session.dataset_info()
        representations = ", ".join(
            item.label for item in info.geometry_representations
        )
        limitations = "\n\n".join(f"• {item}" for item in info.limitations)
        QMessageBox.information(
            self,
            "Mapping provenance and limitations",
            "CF standardizes region names, not boundaries. Displayed shapes and "
            "point matches use a versioned spatial interpretation. Parent matches "
            "come from the configured hierarchy.\n\n"
            f"CF vocabulary: version {info.cf_version} ({info.cf_date})\n"
            f"Region names: {info.region_count}\n"
            f"Spatial profile: {info.profile.id}@{info.profile.version}\n"
            f"Basis: {info.profile.basis}\n"
            f"CRS: {info.crs}\n"
            f"Lookup: {info.area_predicate}, boundary inclusive, "
            f"{info.lookup_geometry_resolution} geometry\n"
            f"Geometry validation: {info.lookup_geometry_validation}\n"
            f"Hierarchy: {info.hierarchy_name} {info.hierarchy_version}\n"
            f"Shape detail: {representations}\n\n"
            f"Limitations\n\n{limitations}",
        )

    def _lookup_from_controls(self) -> None:
        self._map.set_marker(self._longitude.value(), self._latitude.value())
        self._lookup()

    def _lookup_point(self, longitude: float, latitude: float) -> None:
        self._longitude.setValue(longitude)
        self._latitude.setValue(latitude)
        self._lookup()

    def _activate_point(self, longitude: float, latitude: float) -> None:
        self._lookup_point(longitude, latitude)
        if self._results.rowCount() == 0:
            return
        self._results.selectRow(0)
        first = self._results.item(0, 0)
        if first is not None:
            self._show_result(first)

    def _lookup(self) -> None:
        try:
            matches = self._session.lookup(
                longitude=self._longitude.value(),
                latitude=self._latitude.value(),
                section_tolerance_km=self._tolerance.value(),
            )
        except Exception as error:
            self._show_error("Could not resolve coordinate", error)
            return

        self._results.setRowCount(0)
        for row, match in enumerate(matches):
            relation = {
                "ancestor": "Hierarchy parent",
                "covered_by": "Geometry match",
                "near_section": "Near section",
            }[match.relation]
            if match.distance_km is not None:
                relation += f" · {match.distance_km:.2f} km"
            tooltip = (
                f"Relation: {match.relation}\n"
                f"{match.mapping.id}@{match.mapping.version}\n"
                f"{match.method} / {match.predicate}\n"
                f"Source: {match.source.name} {match.source.version}"
            )
            self._add_result_row(row, match.name, relation, tooltip)
        count = len(matches)
        self.statusBar().showMessage(
            f"{count} region{'s' if count != 1 else ''} at "
            f"{self._longitude.value():.6f}, {self._latitude.value():.6f}"
        )

    def _show_result(self, item: QTableWidgetItem) -> None:
        region_name = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(region_name, str):
            self._region.setCurrentText(region_name)
            self._show_region(region_name)

    def _show_selected_region(self) -> None:
        self._show_region(self._region.currentText().strip(), reset_lookup=True)

    def _show_region(self, region_name: str, *, reset_lookup: bool = False) -> None:
        if not region_name:
            return
        try:
            region = self._session.region(region_name)
            info = self._session.dataset_info()
            connected_rows = self._connected_region_rows(region) if reset_lookup else None
            shape = self._session.shape(
                region_name,
                geometry_resolution=self._geometry_resolution(),
            )
            if reset_lookup:
                self._reset_coordinate_lookup()
            self._map.set_selected_geometry(shape, clear_marker=reset_lookup)
        except Exception as error:
            self._show_error("Could not show region", error)
            return

        if connected_rows is not None:
            self._results.setRowCount(0)
            for row, (name, relation) in enumerate(connected_rows):
                self._add_result_row(
                    row,
                    name,
                    relation,
                    "Connected through the configured region hierarchy.",
                )

        hierarchy = " → ".join(region.hierarchy_path) or "—"
        parents = ", ".join(region.parents) or "—"
        description = region.description or "No description provided."
        self._details.setHtml(
            f"<b>{escape(region.name)}</b><br>"
            f"{escape(description)}<br><br>"
            f"<b>Kind:</b> {escape(region.kind)}<br>"
            f"<b>Parents:</b> {escape(parents)}<br>"
            f"<b>Hierarchy:</b> {escape(hierarchy)}<br>"
            f"<b>Mapping:</b> {escape(info.mapping_id)}@{escape(info.mapping_version)}<br>"
            f"<b>Shape detail:</b> {escape(self._geometry_resolution() or 'default')}<br>"
            f"<b>Source:</b> <a href=\"{escape(region.geometry_source_url, quote=True)}\">"
            f"{escape(region.geometry_source)} {escape(region.geometry_source_version)}</a><br>"
            f"<b>License:</b> {escape(region.geometry_license)}<br>"
            f"<b>Method:</b> {escape(region.geometry_method)}"
        )
        was_hidden = self._details_group.isHidden()
        self._details_group.show()
        if was_hidden:
            self._resize_details_panel(self._details_group.is_expanded)
        self._shown_region = region.name
        self.statusBar().showMessage(f"Showing {region.name} ({region.geometry_type})")

    def _connected_region_rows(self, selected: Region) -> list[tuple[str, str]]:
        rows = [(selected.name, "Selected region")]
        seen = {selected.name}
        pending = [(name, True) for name in selected.parents]
        while pending:
            name, direct = pending.pop(0)
            if name in seen:
                continue
            seen.add(name)
            rows.append((name, "Direct parent" if direct else "Hierarchy ancestor"))
            parent = self._session.region(name)
            pending.extend((parent_name, False) for parent_name in parent.parents)
        return rows

    def _add_result_row(
        self,
        row: int,
        region_name: str,
        relation: str,
        tooltip: str,
    ) -> None:
        name_item = QTableWidgetItem(region_name)
        name_item.setData(Qt.ItemDataRole.UserRole, region_name)
        name_item.setToolTip(tooltip)
        relation_item = QTableWidgetItem(relation)
        relation_item.setData(Qt.ItemDataRole.UserRole, region_name)
        relation_item.setToolTip(tooltip)
        self._results.insertRow(row)
        self._results.setItem(row, 0, name_item)
        self._results.setItem(row, 1, relation_item)

    def _reset_coordinate_lookup(self) -> None:
        self._longitude.setValue(0.0)
        self._latitude.setValue(0.0)
        self._tolerance.setValue(0.0)

    def _show_cursor_coordinate(self, longitude: float, latitude: float) -> None:
        self._cursor_coordinate.setText(f"Lon: {longitude:.5f}  Lat: {latitude:.5f}")

    def _clear_cursor_coordinate(self) -> None:
        self._cursor_coordinate.setText("Lon: --  Lat: --")

    def _configure_context_menus(self) -> None:
        self._results.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._results.customContextMenuRequested.connect(
            self._show_results_context_menu
        )

        self._region.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._region.customContextMenuRequested.connect(
            lambda position: self._show_region_context_menu(
                self._region.mapToGlobal(position)
            )
        )
        region_line_edit = self._region.lineEdit()
        if region_line_edit is not None:
            region_line_edit.setContextMenuPolicy(
                Qt.ContextMenuPolicy.CustomContextMenu
            )
            region_line_edit.customContextMenuRequested.connect(
                lambda position: self._show_region_context_menu(
                    region_line_edit.mapToGlobal(position)
                )
            )

        coordinate_widgets: list[QWidget] = [
            self._lookup_group,
            self._longitude,
            self._latitude,
            self._tolerance,
            self._lookup_button,
        ]
        for spin_box in (self._longitude, self._latitude, self._tolerance):
            line_edit = spin_box.lineEdit()
            if line_edit is not None:
                coordinate_widgets.append(line_edit)
        for widget in coordinate_widgets:
            widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            widget.customContextMenuRequested.connect(
                lambda position, source=widget: self._show_coordinate_context_menu(
                    source.mapToGlobal(position)
                )
            )

    def _show_map_context_menu(
        self,
        longitude: float,
        latitude: float,
        global_position: QPoint,
    ) -> None:
        menu = QMenu(self)
        copy_action = menu.addAction("Copy lon/lat")
        if menu.exec(global_position) is copy_action:
            self._copy_lon_lat(longitude, latitude)

    def _show_results_context_menu(self, position: QPoint) -> None:
        item = self._results.itemAt(position)
        if item is not None:
            self._results.selectRow(item.row())
        selected_name = self._selected_result_name()

        menu = QMenu(self._results)
        copy_selected = None
        if selected_name is not None:
            copy_selected = menu.addAction("Copy region name")
        copy_all = menu.addAction("Copy all region names")
        copy_all.setEnabled(self._results.rowCount() > 0)
        chosen = menu.exec(self._results.viewport().mapToGlobal(position))
        if copy_selected is not None and chosen is copy_selected:
            assert selected_name is not None
            self._copy_region_name(selected_name)
        elif chosen is copy_all:
            self._copy_all_region_names()

    def _selected_result_name(self) -> str | None:
        row = self._results.currentRow()
        if row < 0:
            return None
        item = self._results.item(row, 0)
        return item.text() if item is not None else None

    def _show_region_context_menu(self, global_position: QPoint) -> None:
        name = self._region.currentText().strip()
        menu = QMenu(self._region)
        copy_action = menu.addAction("Copy region name")
        copy_action.setEnabled(bool(name))
        if menu.exec(global_position) is copy_action:
            self._copy_region_name(name)

    def _show_coordinate_context_menu(self, global_position: QPoint) -> None:
        menu = QMenu(self._lookup_group)
        copy_action = menu.addAction("Copy lon/lat")
        paste_actions = []
        options = coordinate_paste_options(QApplication.clipboard().text())
        if options:
            menu.addSeparator()
            for label, longitude, latitude in options:
                paste_actions.append(
                    (menu.addAction(label), longitude, latitude)
                )

        chosen = menu.exec(global_position)
        if chosen is copy_action:
            self._copy_lon_lat(self._longitude.value(), self._latitude.value())
            return
        for action, longitude, latitude in paste_actions:
            if chosen is action:
                self._paste_lon_lat(longitude, latitude)
                return

    def _paste_lon_lat(self, longitude: float, latitude: float) -> None:
        self._longitude.setValue(longitude)
        self._latitude.setValue(latitude)
        self.statusBar().showMessage("Pasted longitude and latitude.", 3000)

    def _copy_lon_lat(self, longitude: float, latitude: float) -> None:
        self._copy_text(
            f"{longitude:.6f}, {latitude:.6f}",
            "Copied longitude and latitude.",
        )

    def _copy_region_name(self, region_name: str) -> None:
        self._copy_text(region_name, "Copied region name.")

    def _copy_all_region_names(self) -> None:
        names = []
        for row in range(self._results.rowCount()):
            name_item = self._results.item(row, 0)
            if name_item is not None:
                names.append(name_item.text())
        self._copy_text(", ".join(names), "Copied all region names.")

    def _copy_text(self, text: str, status_message: str) -> None:
        QApplication.clipboard().setText(text)
        self.statusBar().showMessage(status_message, 3000)

    def _show_error(self, title: str, error: Exception) -> None:
        message = str(error.args[0]) if error.args else str(error)
        QMessageBox.critical(self, title, message)
        self.statusBar().showMessage(message)
