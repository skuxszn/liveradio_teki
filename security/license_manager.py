"""
License manifest management for music rights compliance.

Tracks music licenses for all played tracks and provides compliance reporting.
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TrackLicense:
    """License information for a track.

    Attributes:
        id: Unique track identifier
        artist: Artist name
        title: Track title
        license: License type (e.g., "Creative Commons BY 4.0", "Public Domain")
        license_url: URL to license details
        acquired_date: Date license was acquired (ISO format)
        notes: Optional notes about the license
    """

    id: str
    artist: str
    title: str
    license: str
    license_url: str
    acquired_date: str
    notes: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary representation.

        Returns:
            Dictionary with all license fields
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "TrackLicense":
        """Create TrackLicense from dictionary.

        Args:
            data: Dictionary with license fields

        Returns:
            TrackLicense instance
        """
        return cls(
            id=data["id"],
            artist=data["artist"],
            title=data["title"],
            license=data["license"],
            license_url=data["license_url"],
            acquired_date=data["acquired_date"],
            notes=data.get("notes", ""),
        )


class LicenseManifestError(Exception):
    """Exception raised for license manifest errors."""

    pass


class LicenseManager:
    """Manager for music license manifest.

    Handles loading, validation, and querying of music license information.

    Attributes:
        manifest_path: Path to license manifest JSON file
        licenses: Dictionary mapping track IDs to TrackLicense objects
    """

    def __init__(self, manifest_path: str):
        """Initialize license manager.

        Args:
            manifest_path: Path to license manifest JSON file
        """
        self.manifest_path = Path(manifest_path)
        self.licenses: Dict[str, TrackLicense] = {}
        self._load_manifest()

    def _load_manifest(self) -> None:
        """Load license manifest from JSON file.

        Raises:
            LicenseManifestError: If manifest file cannot be loaded or is invalid
        """
        if not self.manifest_path.exists():
            logger.warning(
                f"License manifest not found at {self.manifest_path}, creating empty manifest"
            )
            self._create_empty_manifest()
            return

        try:
            with open(self.manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Validate structure
            if "tracks" not in data:
                raise LicenseManifestError("Invalid manifest format: missing 'tracks' key")

            # Load licenses
            self.licenses = {}
            for track_data in data["tracks"]:
                try:
                    license_info = TrackLicense.from_dict(track_data)
                    self.licenses[license_info.id] = license_info
                except (KeyError, TypeError) as e:
                    logger.error(f"Invalid license entry: {track_data} - {e}")
                    continue

            logger.info(f"Loaded {len(self.licenses)} track licenses from manifest")

        except json.JSONDecodeError as e:
            raise LicenseManifestError(f"Invalid JSON in manifest file: {e}")
        except Exception as e:
            raise LicenseManifestError(f"Error loading manifest: {e}")

    def _create_empty_manifest(self) -> None:
        """Create an empty license manifest file."""
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)

        manifest_data = {
            "version": "1.0",
            "created": datetime.utcnow().isoformat(),
            "tracks": [],
        }

        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        logger.info(f"Created empty license manifest at {self.manifest_path}")

    def save_manifest(self) -> None:
        """Save current licenses to manifest file.

        Raises:
            LicenseManifestError: If manifest cannot be saved
        """
        try:
            manifest_data = {
                "version": "1.0",
                "last_updated": datetime.utcnow().isoformat(),
                "tracks": [license_info.to_dict() for license_info in self.licenses.values()],
            }

            with open(self.manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved {len(self.licenses)} licenses to manifest")

        except Exception as e:
            raise LicenseManifestError(f"Error saving manifest: {e}")

    def get_license(self, track_id: str) -> Optional[TrackLicense]:
        """Get license information for a track.

        Args:
            track_id: Unique track identifier

        Returns:
            TrackLicense if found, None otherwise
        """
        return self.licenses.get(track_id)

    def has_license(self, track_id: str) -> bool:
        """Check if a track has license information.

        Args:
            track_id: Unique track identifier

        Returns:
            True if license exists, False otherwise
        """
        return track_id in self.licenses

    def add_license(self, license_info: TrackLicense) -> None:
        """Add or update license information for a track.

        Args:
            license_info: TrackLicense object to add
        """
        self.licenses[license_info.id] = license_info
        logger.info(f"Added license for track {license_info.id}: {license_info.license}")

    def remove_license(self, track_id: str) -> bool:
        """Remove license information for a track.

        Args:
            track_id: Unique track identifier

        Returns:
            True if license was removed, False if it didn't exist
        """
        if track_id in self.licenses:
            del self.licenses[track_id]
            logger.info(f"Removed license for track {track_id}")
            return True
        return False

    def validate_track(self, track_id: str, artist: str, title: str) -> bool:
        """Validate that a track has proper license information.

        Args:
            track_id: Unique track identifier
            artist: Artist name
            title: Track title

        Returns:
            True if track has valid license, False otherwise
        """
        if not self.has_license(track_id):
            logger.warning(f"Track {track_id} ({artist} - {title}) has no license information")
            return False

        license_info = self.get_license(track_id)
        if not license_info:
            return False

        # Basic validation
        if not license_info.license or not license_info.license_url:
            logger.warning(f"Track {track_id} has incomplete license information")
            return False

        return True

    def get_unlicensed_tracks(self, played_track_ids: List[str]) -> List[str]:
        """Get list of played tracks that lack license information.

        Args:
            played_track_ids: List of track IDs that have been played

        Returns:
            List of track IDs without licenses
        """
        return [track_id for track_id in played_track_ids if not self.has_license(track_id)]

    def generate_compliance_report(self, played_track_ids: List[str]) -> Dict[str, Any]:
        """Generate a compliance report for played tracks.

        Args:
            played_track_ids: List of track IDs that have been played

        Returns:
            Dictionary with compliance statistics and details
        """
        total_tracks = len(set(played_track_ids))
        unlicensed = self.get_unlicensed_tracks(played_track_ids)
        licensed = total_tracks - len(unlicensed)

        # Count licenses by type
        license_types: Dict[str, int] = {}
        for track_id in set(played_track_ids):
            if self.has_license(track_id):
                license_info = self.get_license(track_id)
                if license_info:
                    license_type = license_info.license
                    license_types[license_type] = license_types.get(license_type, 0) + 1

        compliance_rate = (licensed / total_tracks * 100) if total_tracks > 0 else 0

        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "total_tracks_played": total_tracks,
            "licensed_tracks": licensed,
            "unlicensed_tracks": len(unlicensed),
            "compliance_rate": round(compliance_rate, 2),
            "license_types": license_types,
            "unlicensed_track_ids": unlicensed,
        }

        return report

    def export_to_csv(self, output_path: str) -> None:
        """Export license manifest to CSV format.

        Args:
            output_path: Path to output CSV file

        Raises:
            LicenseManifestError: If export fails
        """
        try:
            import csv

            with open(output_path, "w", newline="", encoding="utf-8") as f:
                if not self.licenses:
                    logger.warning("No licenses to export")
                    return

                fieldnames = [
                    "id",
                    "artist",
                    "title",
                    "license",
                    "license_url",
                    "acquired_date",
                    "notes",
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for license_info in self.licenses.values():
                    writer.writerow(license_info.to_dict())

            logger.info(f"Exported {len(self.licenses)} licenses to {output_path}")

        except Exception as e:
            raise LicenseManifestError(f"Error exporting to CSV: {e}")
