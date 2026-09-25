# cf-regions-gui

Native experimental offline desktop application for interactive discovery of [CF Standardized Region List][cf-list] names and their geometries. It uses the separate [`cf-regions`][core] library for coordinate lookup, hierarchy, metadata, and geometry.

> [!IMPORTANT]
> CF standardizes region names, not boundaries. Displayed shapes are a
> documented interpretation for discovery and categorization, not official CF
> boundaries and not suitable for navigation or legal decisions.

## Install and run

Install from PyPI:

```console
pip install cf-regions-gui
```

Run the application:

```console
cfregions-gui
```
### Optional 3D globe view

For an additional native 3D globe view, install the deliberately renderer extra:

```console
pip install "cf-regions-gui[globe]"
```

For the globe view, `PySide6-Addons` is installed, which is much larger than 
the base GUI dependencies. 

### Python entry point

Applications that want to launch the window explicitly can use:

```python
from cfregions_gui import run_gui
raise SystemExit( run_gui() )
```

For programmatic region queries, use `cf-regions` directly. This desktop
package is intentionally only a presentation layer.

## Functionality

- **Coordinate lookup:** Click on the map or enter longitude and latitude. A
  double-click also selects and draws the most-specific match. Pointer
  coordinates appear in the status bar while hovering the map without 
  triggering a lookup.
- **Region selection:** Search the complete region list or double-click a lookup 
  result name to draw its shape. Direct geometry matches and semantic parents remain
  distinguishable.
- **Native 2D map:** Pan, zoom, fit a region, or return to the world view using
  controls embedded in the map. Rendering is tile-free, offline, and follows
  the effective light or dark palette.
- **Shape detail and provenance:** Switch between low- and high-detail display
  geometry without changing the profile-defined lookup representation. Region
  details include source, license, mapping, and derivation method. Shapes retain
  their upstream definitions; for example, the bundled SeaVoX North Sea and
  Baltic Sea representations do not touch.
- **Optional 3D globe:** Rotate, zoom, and perform the same point lookup as on
  the 2D map. Close zoom temporarily uses a higher-resolution local texture.
  The globe remains offline and omits a context menu to preserve touchpad drag
  gestures.
- **Clipboard support:** Copy map or form coordinates, selected region names,
  or all result names. Valid comma-separated values can be pasted as either
  longitude/latitude or latitude/longitude.
- **Profiles and releases:** Select CF releases and spatial interpretation
  profiles. Profile controls stay hidden when only one choice is available.

### Startup options

Choose a historical CF Standardized Region List release or an external self-describing 
spatial interpretation profile at startup:

```console
cfregions-gui --cf-version 3
cfregions-gui --profile cfregions-default --profile-version 2026.09.1
cfregions-gui --data-directory /path/to/data
cfregions-gui --profile-directory /path/to/additional-profiles
python -m cfregions_gui
```

### Options

- `--cf-version` selects a historical CF release. The default is the latest release.
- `--profile` and `--profile-version` select a spatial interpretation profile. 
  The default is the built-in `cfregions-default` profile. 
- `--data-directory` replaces the complete built-in data root of the 
  underlying `cf-regions` library.
- `--profile-directory` is repeatable and adds auto-discovered profiles while
  retaining the built-in CF data and default profile. 

## Authors and maintainership

`cf-regions-gui` was initiated and originally developed by
[Yves Sorge](https://github.com/ysorge) during the
[CF Conventions Community Workshop 2026][workshop] at ECMWF in Bonn, Germany.
The project is currently maintained by its original author.

Additional contributors are recorded in [AUTHORS.md](AUTHORS.md) and the
repository history. Maintainer responsibility may move to another person or
organization without replacing the authorship of existing contributions.

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
