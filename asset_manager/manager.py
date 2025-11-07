"""
Asset Manager - Main orchestrator for video asset management.

This module provides a high-level interface for validating, managing,
and serving video loop assets.
"""

import logging
from pathlib import Path
from typing import Optional

from asset_manager.config import AssetConfig, get_config
from asset_manager.overlay_generator import OverlayGenerator
from asset_manager.validator import ValidationResult, VideoValidator

logger = logging.getLogger(__name__)


class AssetManager:
    """
    High-level asset management interface.

    This class orchestrates video validation, metadata extraction,
    overlay generation, and asset cleanup.
    """

    def __init__(self, config: Optional[AssetConfig] = None):
        """
        Initialize the asset manager.

        Args:
            config: Asset configuration. If None, uses default config.
        """
        self.config = config or get_config()
        self.validator = VideoValidator(self.config)
        self.overlay_generator = OverlayGenerator(self.config)
        self.logger = logging.getLogger(__name__)

    def validate_loop(self, file_path: str) -> ValidationResult:
        """
        Validate a video loop file.

        This is a convenience wrapper around VideoValidator.validate_loop().

        Args:
            file_path: Path to the video file

        Returns:
            ValidationResult with validation status and errors
        """
        return self.validator.validate_loop(file_path)

    def get_loop_metadata(self, file_path: str) -> dict:
        """
        Extract metadata from a video loop file.

        Args:
            file_path: Path to the video file

        Returns:
            Dictionary with video metadata

        Raises:
            RuntimeError: If metadata extraction fails
        """
        try:
            metadata = self.validator.get_loop_metadata(file_path)
            return metadata.to_dict()
        except Exception as e:
            self.logger.error(f"Failed to extract metadata from {file_path}: {e}")
            raise RuntimeError(f"Metadata extraction failed: {e}")

    def generate_overlay(
        self,
        artist: str,
        title: str,
        template: Optional[str] = None,
        album: Optional[str] = None,
    ) -> str:
        """
        Generate a PNG overlay with track information.

        Args:
            artist: Artist name
            title: Song title
            template: Optional template name
            album: Optional album name

        Returns:
            Absolute path to the generated overlay PNG

        Raises:
            RuntimeError: If overlay generation fails
        """
        return self.overlay_generator.generate_overlay(artist, title, template, album)

    def cleanup_old_overlays(self, older_than_hours: Optional[int] = None) -> int:
        """
        Remove overlay files older than specified hours.

        Args:
            older_than_hours: Age threshold in hours. If None, uses config value.

        Returns:
            Number of files deleted
        """
        return self.overlay_generator.cleanup_old_overlays(older_than_hours)

    def ensure_default_loop_exists(self) -> bool:
        """
        Verify that the default loop file exists and is valid.

        Returns:
            True if default loop exists and is valid, False otherwise
        """
        default_path = self.config.default_loop_path

        if not Path(default_path).exists():
            self.logger.error(f"Default loop does not exist: {default_path}")
            return False

        result = self.validate_loop(default_path)
        if not result.valid:
            self.logger.error(f"Default loop validation failed: {', '.join(result.errors)}")
            return False

        self.logger.info(f"Default loop is valid: {default_path}")
        return True

    def get_loop_or_default(self, file_path: str) -> str:
        """
        Get a loop file path, falling back to default if invalid.

        This method validates the requested loop and returns either the
        validated loop path or the default loop path if validation fails.

        Args:
            file_path: Requested loop file path

        Returns:
            Validated loop path or default loop path
        """
        # Check if requested file exists
        if not Path(file_path).exists():
            self.logger.warning(f"Loop file does not exist: {file_path}, using default")
            return self.config.default_loop_path

        # Validate the loop
        result = self.validate_loop(file_path)
        if not result.valid:
            self.logger.warning(
                f"Loop validation failed for {file_path}: {', '.join(result.errors)}, "
                "using default"
            )
            return self.config.default_loop_path

        # Return validated path
        return file_path

    def validate_all_loops_in_directory(self, directory: Optional[str] = None) -> dict:
        """
        Validate all loop files in a directory.

        Args:
            directory: Directory to scan. If None, uses tracks directory.

        Returns:
            Dictionary with validation statistics:
            {
                "total": int,
                "valid": int,
                "invalid": int,
                "errors": [{"file": str, "errors": [str]}]
            }
        """
        dir_path: Path
        if directory is None:
            dir_path = Path(self.config.loops_base_path) / "tracks"
        else:
            dir_path = Path(directory)

        if not dir_path.exists():
            self.logger.error(f"Directory does not exist: {dir_path}")
            return {"total": 0, "valid": 0, "invalid": 0, "errors": []}

        results: dict = {
            "total": 0,
            "valid": 0,
            "invalid": 0,
            "errors": [],
        }

        # Find all MP4 files
        for loop_file in dir_path.glob("*.mp4"):
            results["total"] += 1
            result = self.validate_loop(str(loop_file))

            if result.valid:
                results["valid"] += 1
            else:
                results["invalid"] += 1
                results["errors"].append(
                    {
                        "file": str(loop_file),
                        "errors": result.errors,
                    }
                )

        self.logger.info(
            f"Validated {results['total']} loops in {dir_path}: "
            f"{results['valid']} valid, {results['invalid']} invalid"
        )

        return results

    def get_storage_stats(self) -> dict:
        """
        Get storage statistics for loop assets.

        Returns:
            Dictionary with storage information:
            {
                "loops_count": int,
                "overlays_count": int,
                "total_size_mb": float,
                "loops_size_mb": float,
                "overlays_size_mb": float
            }
        """
        loops_path = Path(self.config.loops_base_path)
        overlays_path = Path(self.config.overlays_path)

        stats = {
            "loops_count": 0,
            "overlays_count": 0,
            "total_size_mb": 0.0,
            "loops_size_mb": 0.0,
            "overlays_size_mb": 0.0,
        }

        # Count loops and size
        if loops_path.exists():
            loops_size = 0
            for loop_file in loops_path.rglob("*.mp4"):
                stats["loops_count"] += 1
                try:
                    loops_size += loop_file.stat().st_size
                except Exception:
                    pass
            stats["loops_size_mb"] = loops_size / (1024 * 1024)

        # Count overlays and size
        if overlays_path.exists():
            overlays_size = 0
            for overlay_file in overlays_path.glob("*.png"):
                stats["overlays_count"] += 1
                try:
                    overlays_size += overlay_file.stat().st_size
                except Exception:
                    pass
            stats["overlays_size_mb"] = overlays_size / (1024 * 1024)

        stats["total_size_mb"] = stats["loops_size_mb"] + stats["overlays_size_mb"]

        return stats
