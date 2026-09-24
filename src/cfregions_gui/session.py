"""Small stateful adapter between the desktop UI and :mod:`cfregions`."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cfregions
from cfregions import DatasetInfo, Region, RegionMatch, SpatialInterpretationProfile


@dataclass(slots=True)
class RegionSession:
    """Keep dataset selection explicit while presenting a convenient UI facade."""

    cf_version: str = "current"
    profile: str = "default"
    profile_version: str = "current"
    data_directory: Path | None = None
    profile_directories: tuple[Path, ...] = ()

    def versions(self) -> tuple[str, ...]:
        return cfregions.list_cf_versions(data_directory=self.data_directory)

    def profiles(self) -> tuple[SpatialInterpretationProfile, ...]:
        return cfregions.list_spatial_profiles(
            data_directory=self.data_directory,
            profile_directories=self.profile_directories,
        )

    def dataset_info(self) -> DatasetInfo:
        return cfregions.get_dataset_info(
            cf_version=self.cf_version,
            profile=self.profile,
            profile_version=self.profile_version,
            data_directory=self.data_directory,
            profile_directories=self.profile_directories,
        )

    def regions(self) -> tuple[Region, ...]:
        return cfregions.list_regions(
            cf_version=self.cf_version,
            profile=self.profile,
            profile_version=self.profile_version,
            data_directory=self.data_directory,
            profile_directories=self.profile_directories,
        )

    def set_cf_version(self, cf_version: str) -> DatasetInfo:
        """Validate and select a release, returning its provenance."""

        previous = self.cf_version
        self.cf_version = cf_version
        try:
            return self.dataset_info()
        except Exception:
            self.cf_version = previous
            raise

    def set_profile(self, profile: str, profile_version: str) -> DatasetInfo:
        """Validate and select one exact spatial-profile version."""

        previous = (self.profile, self.profile_version)
        self.profile = profile
        self.profile_version = profile_version
        try:
            return self.dataset_info()
        except Exception:
            self.profile, self.profile_version = previous
            raise

    def set_selection(
        self,
        *,
        cf_version: str,
        profile: str,
        profile_version: str,
    ) -> DatasetInfo:
        """Validate and atomically select a compatible CF/profile combination."""

        previous = (self.cf_version, self.profile, self.profile_version)
        self.cf_version = cf_version
        self.profile = profile
        self.profile_version = profile_version
        try:
            return self.dataset_info()
        except Exception:
            self.cf_version, self.profile, self.profile_version = previous
            raise

    def lookup(
        self,
        *,
        longitude: float,
        latitude: float,
        section_tolerance_km: float = 0.0,
        include_ancestors: bool = True,
    ) -> tuple[RegionMatch, ...]:
        return cfregions.match_regions(
            longitude=longitude,
            latitude=latitude,
            section_tolerance_km=section_tolerance_km,
            include_ancestors=include_ancestors,
            cf_version=self.cf_version,
            profile=self.profile,
            profile_version=self.profile_version,
            data_directory=self.data_directory,
            profile_directories=self.profile_directories,
        )

    def region(self, region_name: str) -> Region:
        return cfregions.get_region(
            region_name=region_name,
            cf_version=self.cf_version,
            profile=self.profile,
            profile_version=self.profile_version,
            data_directory=self.data_directory,
            profile_directories=self.profile_directories,
        )

    def shape(
        self,
        region_name: str,
        *,
        geometry_resolution: str | None = None,
    ) -> dict[str, Any]:
        return cfregions.get_region_shape(
            region_name=region_name,
            geometry_resolution=geometry_resolution,
            cf_version=self.cf_version,
            profile=self.profile,
            profile_version=self.profile_version,
            data_directory=self.data_directory,
            profile_directories=self.profile_directories,
        )
