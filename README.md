# cf-regions-gui

`cf-regions-gui` is a native, completely offline desktop map for the
[CF Standardized Region List][cf-list]. It uses the separate [`cf-regions`][core]
library for versioned coordinate lookup, hierarchy, metadata, and geometry.

The application opens an ordinary operating-system window. It has no embedded
browser, local HTTP server, HTML, remote tiles, or network requests. PySide6
draws a compact vector world map from the land geometry bundled with
`cf-regions`. Native controls and map colors automatically follow the effective
system light or dark palette, including theme changes while the application is
running.

An optional native 3D globe uses Qt Quick 3D and locally generated textures.
It remains completely offline and adds no browser or server component.

> CF standardizes region names, not boundaries. Displayed shapes are a
> documented interpretation for discovery and categorization, not official CF
> boundaries and not suitable for navigation or legal decisions.

## Install and run

Python 3.10 or newer is required.

```console
python -m pip install cf-regions-gui
cfregions-gui
```

For the native 3D globe, install the deliberately optional renderer extra:

```console
python -m pip install "cf-regions-gui[globe]"
```

The globe extra installs `PySide6-Addons`, which is much larger than the base
GUI dependencies. Without it, the application simply retains its existing 2D
map and does not show the 3D map-view switch. If a system cannot initialize the
3D graphics backend, the application reports that condition and remains on the
working 2D map.

Select a spatial profile and CF release, then either click the map or enter longitude and latitude.
Profile controls remain hidden when only one profile/version is available.
Double-clicking the map also displays and selects the first, most-specific match.
Double-click a result to draw it. You can also search the complete region list
and choose **Show region**. Drag to pan and use the mouse wheel or in-map
controls to zoom. World, region-fit, zoom, and projection controls float inside
the map so their scope is distinct from application-wide commands.
The status bar shows the longitude and latitude beneath the pointer; this is a
display-only calculation and does not run a region lookup.

Native context menus can copy the coordinate at a 2D map position, the coordinate
form values, one selected region name, or all names in the current result table.
When the clipboard contains two comma-separated numbers, the coordinate form
also offers **Paste lon/lat** and/or **Paste lat/lon** whenever the corresponding
interpretation has valid coordinate ranges. Coordinates copied by the application
use `longitude, latitude` with six decimal places; multiple names are separated by
a comma and space.

The **Region shape detail** control switches the selected region between a
compact low-resolution shape and a larger, slower high-resolution shape. The
world background deliberately stays compact, so changing detail does not make
the complete map pause or consume high-detail memory. This only affects
drawing: coordinate lookup remains pinned to the mapping's declared lookup
representation. Region details show mapping, source, license, and derivation
method; semantic parent results are labelled separately.

On the globe, close zoom automatically doubles the selected texture resolution
after a short pause. Zooming back out releases the larger texture. The bounded
two-tier behavior improves detail without continuously regenerating textures or
retaining maximum-resolution graphics memory.

The shapes preserve their upstream definitions rather than filling gaps by
hand. In particular, the bundled SeaVoX North Sea and Baltic Sea
representations do not touch.

The selected-region details below the map can be resized with the horizontal
splitter or collapsed to its title bar with the button on the right. Dragging
the splitter fully down also collapses the content; dragging it back up expands
it again. Expanding restores the previous useful height.

When available, select **3D globe** inside the map view. Drag to rotate, use the
mouse wheel or map controls to zoom, and click the sphere to perform the same
coordinate lookup as in the 2D map. Land, selected shapes, sections, and the
point marker are rendered from the bundled data into an equirectangular texture
at the selected detail level. Nothing is downloaded at runtime. The globe has no
context menu so touchpad press-and-drag gestures remain dedicated to rotation.

Choose a historical release or an external self-describing dataset at startup:

```console
cfregions-gui --cf-version 3
cfregions-gui --profile cfregions-default --profile-version 2026.09.1
cfregions-gui --data-directory /path/to/data
cfregions-gui --profile-directory /path/to/additional-profiles
python -m cfregions_gui
```

`--profile-directory` is repeatable and adds auto-discovered profiles while
retaining the built-in CF data and default profile. `--data-directory` instead
replaces the complete data root.

## Python entry point

Applications that want to launch the window explicitly can use:

```python
from cfregions_gui import run_gui

raise SystemExit(
    run_gui(
        cf_version="current",
        profile="default",
        profile_version="current",
    )
)
```

For programmatic region queries, depend directly on `cf-regions`; this desktop
package is intentionally only a presentation layer.

## Authors and maintainership

`cf-regions-gui` was initiated and originally developed by
[Yves Sorge](https://github.com/ysorge) during the
[CF Conventions Community Workshop 2026][workshop] at ECMWF in Bonn, Germany.
The project is currently maintained by its original author.

Additional contributors are recorded in [AUTHORS.md](AUTHORS.md) and the
repository history. Maintainer responsibility may move to another person or
organization without replacing the authorship of existing contributions.

## Architecture

- `session.py` adapts the stable `cfregions` API to one selected dataset.
- `geometry.py` turns GeoJSON into presentation-neutral drawing primitives.
- `map_canvas.py` renders and navigates the tile-free vector world map.
- `map_views.py` synchronizes the 2D map and lazily created optional globe.
- `map_viewport.py` provides map-scoped navigation and projection controls.
- `globe.py` contains the small Qt Quick 3D adapter and picking bridge.
- `globe_texture.py` renders bundled geometry into local sphere textures.
- `window.py` owns native controls and user interaction.
- `app.py` and `cli.py` contain process startup only.

This keeps core geography independent from Qt and keeps the desktop application
independent from `cf-regions-map`, FastAPI, Uvicorn, MapLibre, and WebEngine.

## Development

Install the application and its development dependencies from this repository:

```console
python -m pip install -e ".[dev,globe]"
pytest
```

For coordinated development against a sibling checkout of the core library,
use `python -m pip install -e ../cf-regions -e ".[dev,globe]"` instead.

## Contributing

Contributions are welcome through issues and pull requests. Please open an
issue first for substantial features, API changes, or interface redesigns;
small fixes and documentation improvements may be submitted directly. See
[CONTRIBUTING.md](CONTRIBUTING.md) and the [Code of conduct](CODE_OF_CONDUCT.md).

## License

Code is licensed under [GNU GPL v3.0 or later](LICENSE)
(`GPL-3.0-or-later`). Geometry and vocabulary data are distributed by
`cf-regions`; see its data-license documentation for attribution and source
terms.

[cf-list]: https://cfconventions.org/Data/standardized-region-list/standardized-region-list.current.html
[core]: https://github.com/ysorge/cf-regions
