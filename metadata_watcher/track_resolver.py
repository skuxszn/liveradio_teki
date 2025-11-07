"""Track resolver for mapping AzuraCast tracks to video loops.

Handles track identification, normalization, and loop file resolution.
"""

import logging
from pathlib import Path
from typing import Optional
import os

from .config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)


class TrackResolver:
    """Resolves track metadata to video loop file paths."""

    def __init__(self, config: Config):
        """Initialize track resolver.

        Args:
            config: Application configuration.
        """
        self.config = config
        self.loops_path = config.loops_path
        self.default_loop = config.default_loop

        # Initialize database connection for track mappings
        try:
            db_url = os.getenv(
                "DATABASE_URL",
                f"postgresql://{config.postgres_user}:{config.postgres_password}@{config.postgres_host}:{config.postgres_port}/{config.postgres_db}",
            )
            engine = create_engine(db_url)
            SessionLocal = sessionmaker(bind=engine)
            self.db_session = SessionLocal()
            logger.info("Track resolver connected to database for track mappings")
        except Exception as e:
            logger.warning(f"Failed to connect to database for track mappings: {e}")
            self.db_session = None

    def resolve_loop(
        self,
        artist: str,
        title: str,
        song_id: Optional[str] = None,
        album: Optional[str] = None,
    ) -> Path:
        """Resolve a track to its video loop file.

        Primary key: {artist} - {title} (normalized)
        Fallback: AzuraCast song ID
        Last resort: Default loop

        Args:
            artist: Artist name.
            title: Song title.
            song_id: Optional AzuraCast song ID.
            album: Optional album name (for logging).

        Returns:
            Path: Absolute path to video loop file.
        """
        track_key = self._normalize_track_key(artist, title)
        logger.info(f"Resolving loop for: {track_key} (song_id={song_id})")

        # Try track-specific loop (artist - title)
        loop_path = self._find_loop_by_track_key(track_key)
        if loop_path:
            logger.info(f"Found track-specific loop: {loop_path}")
            return loop_path

        # Try song ID based loop
        if song_id:
            loop_path = self._find_loop_by_song_id(song_id)
            if loop_path:
                logger.info(f"Found song ID loop: {loop_path}")
                return loop_path

        # Fall back to default loop
        logger.warning(
            f"No specific loop found for '{track_key}', using default: {self.default_loop}"
        )
        return self.default_loop

    def _normalize_track_key(self, artist: str, title: str) -> str:
        """Normalize track key for consistent matching.

        Normalization:
        - Lowercase
        - Strip whitespace
        - Remove special characters that might cause filesystem issues

        Args:
            artist: Artist name.
            title: Song title.

        Returns:
            str: Normalized track key in format "artist - title".
        """
        # Basic normalization
        artist_norm = artist.lower().strip()
        title_norm = title.lower().strip()

        # Remove problematic characters for filesystem
        chars_to_remove = ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]
        for char in chars_to_remove:
            artist_norm = artist_norm.replace(char, "")
            title_norm = title_norm.replace(char, "")

        # Collapse multiple spaces
        artist_norm = " ".join(artist_norm.split())
        title_norm = " ".join(title_norm.split())

        return f"{artist_norm} - {title_norm}"

    def _find_loop_by_track_key(self, track_key: str) -> Optional[Path]:
        """Find loop file by normalized track key.

        First checks database track_mappings table, then falls back to filesystem.

        Args:
            track_key: Normalized track key.

        Returns:
            Path if found and valid, None otherwise.
        """
        # Try database first
        if self.db_session:
            try:
                from sqlalchemy import text

                result = self.db_session.execute(
                    text(
                        "SELECT loop_file_path FROM track_mappings WHERE track_key = :key AND is_active = true"
                    ),
                    {"key": track_key},
                ).first()

                if result:
                    loop_file_path = result[0]
                    loop_path = Path(loop_file_path)
                    logger.info(f"Found track mapping in database: {track_key} → {loop_file_path}")
                    if self._is_valid_loop(loop_path):
                        return loop_path
                    else:
                        logger.warning(
                            f"Database mapping exists but file not found: {loop_file_path}"
                        )
            except Exception as e:
                logger.error(f"Database lookup failed for {track_key}: {e}")

        # Fallback: Try filesystem-based lookup
        # Convert track key to filename-safe format
        filename = track_key.replace(" ", "_") + ".mp4"

        # Try tracks subdirectory first
        tracks_dir = self.loops_path / "tracks"
        loop_path = tracks_dir / filename
        if self._is_valid_loop(loop_path):
            logger.info(f"Found track file in tracks/: {loop_path}")
            return loop_path

        # Try root loops directory
        loop_path = self.loops_path / filename
        if self._is_valid_loop(loop_path):
            logger.info(f"Found track file in loops root: {loop_path}")
            return loop_path

        return None

    def _find_loop_by_song_id(self, song_id: str) -> Optional[Path]:
        """Find loop file by AzuraCast song ID.

        Looks for: {loops_path}/tracks/track_{song_id}_loop.mp4

        Args:
            song_id: AzuraCast song ID.

        Returns:
            Path if found and valid, None otherwise.
        """
        tracks_dir = self.loops_path / "tracks"
        loop_path = tracks_dir / f"track_{song_id}_loop.mp4"

        if self._is_valid_loop(loop_path):
            return loop_path

        return None

    def _is_valid_loop(self, path: Path) -> bool:
        """Check if a loop file is valid.

        Args:
            path: Path to check.

        Returns:
            bool: True if file exists and is readable, False otherwise.
        """
        if not path.exists():
            return False

        if not path.is_file():
            logger.warning(f"Loop path is not a file: {path}")
            return False

        # Check file extension
        if path.suffix.lower() not in [".mp4", ".mkv", ".avi"]:
            logger.warning(f"Invalid video file extension: {path}")
            return False

        # Check file is readable and non-zero size
        try:
            size = path.stat().st_size
            if size == 0:
                logger.warning(f"Loop file is empty: {path}")
                return False
        except OSError as e:
            logger.error(f"Cannot read loop file {path}: {e}")
            return False

        return True

    def get_default_loop(self) -> Path:
        """Get the default loop file path.

        Returns:
            Path: Default loop file path.

        Raises:
            FileNotFoundError: If default loop doesn't exist.
        """
        if not self._is_valid_loop(self.default_loop):
            raise FileNotFoundError(f"Default loop file not found or invalid: {self.default_loop}")
        return self.default_loop
