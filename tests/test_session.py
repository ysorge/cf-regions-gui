from cfregions_gui.session import RegionSession


def test_session_switches_version_and_delegates_lookup() -> None:
    session = RegionSession(cf_version="1")

    assert session.dataset_info().cf_version == "1"
    assert len(session.regions()) == 52
    assert session.set_cf_version("current").cf_version == "5"
    assert "global_land" in {
        match.name for match in session.lookup(longitude=13.405, latitude=52.52)
    }
    profile = session.profiles()[0]
    selected = session.set_profile(profile.id, profile.version)
    assert selected.profile == profile


def test_session_returns_shape_and_metadata() -> None:
    session = RegionSession()

    region = session.region("mediterranean_sea")
    shape = session.shape(region.name)
    detailed = session.shape(region.name, geometry_resolution="high")

    assert region.name == "mediterranean_sea"
    assert shape["type"] == "Feature"
    assert shape["geometry"]["type"] in {"Polygon", "MultiPolygon"}
    assert shape["properties"]["geometry_resolution"] == "low"
    assert detailed["properties"]["geometry_resolution"] == "high"
