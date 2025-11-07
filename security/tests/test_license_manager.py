"""
Tests for license manager module.
"""

import json
import tempfile
from pathlib import Path

import pytest

from security.license_manager import (
    LicenseManager,
    LicenseManifestError,
    TrackLicense,
)


class TestTrackLicense:
    """Tests for TrackLicense dataclass."""

    def test_create_track_license(self):
        """Test creating a TrackLicense."""
        license_info = TrackLicense(
            id="track_123",
            artist="Test Artist",
            title="Test Song",
            license="Creative Commons BY 4.0",
            license_url="https://creativecommons.org/licenses/by/4.0/",
            acquired_date="2025-01-15",
            notes="Test notes",
        )

        assert license_info.id == "track_123"
        assert license_info.artist == "Test Artist"
        assert license_info.title == "Test Song"
        assert license_info.license == "Creative Commons BY 4.0"
        assert license_info.license_url == "https://creativecommons.org/licenses/by/4.0/"
        assert license_info.acquired_date == "2025-01-15"
        assert license_info.notes == "Test notes"

    def test_to_dict(self):
        """Test converting TrackLicense to dictionary."""
        license_info = TrackLicense(
            id="track_123",
            artist="Test Artist",
            title="Test Song",
            license="Creative Commons BY 4.0",
            license_url="https://creativecommons.org/licenses/by/4.0/",
            acquired_date="2025-01-15",
        )

        result = license_info.to_dict()

        assert isinstance(result, dict)
        assert result["id"] == "track_123"
        assert result["artist"] == "Test Artist"
        assert result["title"] == "Test Song"
        assert result["license"] == "Creative Commons BY 4.0"

    def test_from_dict(self):
        """Test creating TrackLicense from dictionary."""
        data = {
            "id": "track_456",
            "artist": "Another Artist",
            "title": "Another Song",
            "license": "Public Domain",
            "license_url": "https://publicdomain.org",
            "acquired_date": "2025-02-01",
            "notes": "Public domain work",
        }

        license_info = TrackLicense.from_dict(data)

        assert license_info.id == "track_456"
        assert license_info.artist == "Another Artist"
        assert license_info.title == "Another Song"
        assert license_info.license == "Public Domain"
        assert license_info.notes == "Public domain work"


class TestLicenseManager:
    """Tests for LicenseManager."""

    @pytest.fixture
    def temp_manifest(self):
        """Create a temporary manifest file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            manifest_data = {
                "version": "1.0",
                "created": "2025-01-01T00:00:00",
                "tracks": [
                    {
                        "id": "track_1",
                        "artist": "Artist 1",
                        "title": "Song 1",
                        "license": "CC BY 4.0",
                        "license_url": "https://creativecommons.org/licenses/by/4.0/",
                        "acquired_date": "2025-01-01",
                        "notes": "",
                    },
                    {
                        "id": "track_2",
                        "artist": "Artist 2",
                        "title": "Song 2",
                        "license": "Public Domain",
                        "license_url": "https://publicdomain.org",
                        "acquired_date": "2025-01-02",
                        "notes": "Test",
                    },
                ],
            }
            json.dump(manifest_data, f)
            temp_path = f.name

        yield temp_path

        # Cleanup
        Path(temp_path).unlink(missing_ok=True)

    @pytest.fixture
    def empty_manifest_path(self):
        """Get path for a non-existent manifest file."""
        temp_dir = tempfile.mkdtemp()
        manifest_path = Path(temp_dir) / "test_manifest.json"
        yield str(manifest_path)
        # Cleanup
        if manifest_path.exists():
            manifest_path.unlink()
        Path(temp_dir).rmdir()

    def test_load_existing_manifest(self, temp_manifest):
        """Test loading an existing manifest file."""
        manager = LicenseManager(temp_manifest)

        assert len(manager.licenses) == 2
        assert "track_1" in manager.licenses
        assert "track_2" in manager.licenses
        assert manager.licenses["track_1"].artist == "Artist 1"
        assert manager.licenses["track_2"].license == "Public Domain"

    def test_load_nonexistent_manifest(self, empty_manifest_path):
        """Test loading a non-existent manifest creates empty file."""
        manager = LicenseManager(empty_manifest_path)

        assert len(manager.licenses) == 0
        assert Path(empty_manifest_path).exists()

    def test_load_invalid_json(self):
        """Test loading invalid JSON raises error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json {")
            temp_path = f.name

        try:
            with pytest.raises(LicenseManifestError, match="Invalid JSON"):
                LicenseManager(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_load_invalid_structure(self):
        """Test loading manifest with invalid structure."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"invalid": "structure"}, f)
            temp_path = f.name

        try:
            with pytest.raises(LicenseManifestError, match="missing 'tracks' key"):
                LicenseManager(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_get_license(self, temp_manifest):
        """Test getting license information for a track."""
        manager = LicenseManager(temp_manifest)

        license_info = manager.get_license("track_1")
        assert license_info is not None
        assert license_info.artist == "Artist 1"
        assert license_info.title == "Song 1"

    def test_get_license_not_found(self, temp_manifest):
        """Test getting license for non-existent track."""
        manager = LicenseManager(temp_manifest)

        license_info = manager.get_license("track_999")
        assert license_info is None

    def test_has_license(self, temp_manifest):
        """Test checking if track has license."""
        manager = LicenseManager(temp_manifest)

        assert manager.has_license("track_1") is True
        assert manager.has_license("track_2") is True
        assert manager.has_license("track_999") is False

    def test_add_license(self, empty_manifest_path):
        """Test adding a license."""
        manager = LicenseManager(empty_manifest_path)

        new_license = TrackLicense(
            id="track_new",
            artist="New Artist",
            title="New Song",
            license="CC BY-SA 4.0",
            license_url="https://creativecommons.org/licenses/by-sa/4.0/",
            acquired_date="2025-03-01",
        )

        manager.add_license(new_license)

        assert manager.has_license("track_new")
        assert manager.licenses["track_new"].artist == "New Artist"

    def test_remove_license(self, temp_manifest):
        """Test removing a license."""
        manager = LicenseManager(temp_manifest)

        assert manager.has_license("track_1")

        result = manager.remove_license("track_1")
        assert result is True
        assert not manager.has_license("track_1")

        # Removing non-existent license
        result = manager.remove_license("track_999")
        assert result is False

    def test_save_manifest(self, empty_manifest_path):
        """Test saving manifest to file."""
        manager = LicenseManager(empty_manifest_path)

        # Add some licenses
        manager.add_license(
            TrackLicense(
                id="track_a",
                artist="Artist A",
                title="Song A",
                license="CC BY 4.0",
                license_url="https://example.com",
                acquired_date="2025-01-01",
            )
        )

        manager.save_manifest()

        # Verify file contents
        with open(empty_manifest_path, "r") as f:
            data = json.load(f)

        assert "tracks" in data
        assert len(data["tracks"]) == 1
        assert data["tracks"][0]["id"] == "track_a"

    def test_validate_track_valid(self, temp_manifest):
        """Test validating a track with valid license."""
        manager = LicenseManager(temp_manifest)

        result = manager.validate_track("track_1", "Artist 1", "Song 1")
        assert result is True

    def test_validate_track_missing_license(self, temp_manifest):
        """Test validating a track without license."""
        manager = LicenseManager(temp_manifest)

        result = manager.validate_track("track_999", "Unknown", "Unknown")
        assert result is False

    def test_validate_track_incomplete_license(self, empty_manifest_path):
        """Test validating a track with incomplete license info."""
        manager = LicenseManager(empty_manifest_path)

        # Add incomplete license
        incomplete_license = TrackLicense(
            id="track_incomplete",
            artist="Artist",
            title="Song",
            license="",  # Missing license type
            license_url="",  # Missing URL
            acquired_date="2025-01-01",
        )
        manager.add_license(incomplete_license)

        result = manager.validate_track("track_incomplete", "Artist", "Song")
        assert result is False

    def test_get_unlicensed_tracks(self, temp_manifest):
        """Test getting list of unlicensed tracks."""
        manager = LicenseManager(temp_manifest)

        played_tracks = ["track_1", "track_2", "track_3", "track_4"]
        unlicensed = manager.get_unlicensed_tracks(played_tracks)

        assert len(unlicensed) == 2
        assert "track_3" in unlicensed
        assert "track_4" in unlicensed
        assert "track_1" not in unlicensed

    def test_generate_compliance_report(self, temp_manifest):
        """Test generating compliance report."""
        manager = LicenseManager(temp_manifest)

        played_tracks = ["track_1", "track_2", "track_3", "track_1", "track_2"]
        report = manager.generate_compliance_report(played_tracks)

        assert report["total_tracks_played"] == 3  # Unique tracks
        assert report["licensed_tracks"] == 2
        assert report["unlicensed_tracks"] == 1
        assert report["compliance_rate"] == pytest.approx(66.67, rel=0.01)
        assert "track_3" in report["unlicensed_track_ids"]
        assert "CC BY 4.0" in report["license_types"]
        assert "Public Domain" in report["license_types"]

    def test_generate_compliance_report_empty(self, empty_manifest_path):
        """Test generating compliance report with no tracks."""
        manager = LicenseManager(empty_manifest_path)

        report = manager.generate_compliance_report([])

        assert report["total_tracks_played"] == 0
        assert report["licensed_tracks"] == 0
        assert report["unlicensed_tracks"] == 0
        assert report["compliance_rate"] == 0

    def test_export_to_csv(self, temp_manifest):
        """Test exporting license manifest to CSV."""
        manager = LicenseManager(temp_manifest)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            csv_path = f.name

        try:
            manager.export_to_csv(csv_path)

            # Verify CSV contents
            with open(csv_path, "r") as f:
                content = f.read()

            assert "track_1" in content
            assert "track_2" in content
            assert "Artist 1" in content
            assert "CC BY 4.0" in content
        finally:
            Path(csv_path).unlink()

    def test_export_to_csv_empty(self, empty_manifest_path):
        """Test exporting empty manifest to CSV."""
        manager = LicenseManager(empty_manifest_path)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            csv_path = f.name

        try:
            manager.export_to_csv(csv_path)
            # Should not raise an error, just create empty/header-only CSV
        finally:
            Path(csv_path).unlink()


