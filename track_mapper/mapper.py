"""Track Mapper - Track to Video Loop Mapping

Maps tracks to video loop files with database backing and LRU caching.
"""

import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

from sqlalchemy import create_engine, text, Engine
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.pool import QueuePool

from track_mapper.config import TrackMapperConfig

logger = logging.getLogger(__name__)


class TrackMapper:
    """Maps tracks to video loop files using PostgreSQL with LRU caching.

    Features:
    - Normalized track key lookup (artist - title)
    - Fallback to AzuraCast song ID
    - Default loop for unmapped tracks
    - LRU caching (1000 entries) to reduce DB queries
    - File validation before returning paths
    - Play count tracking

    Example:
        >>> config = TrackMapperConfig.from_env()
        >>> mapper = TrackMapper(config)
        >>> loop_path = mapper.get_loop("Artist Name", "Song Title")
        >>> print(loop_path)
        '/srv/loops/tracks/artist_name_-_song_title.mp4'
    """

    def __init__(self, config: TrackMapperConfig):
        """Initialize TrackMapper with configuration.

        Args:
            config: TrackMapperConfig instance with database and path settings

        Raises:
            ValueError: If configuration is invalid
            SQLAlchemyError: If database connection fails
        """
        config.validate()
        self.config = config
        self.engine: Engine = self._create_engine()
        self._cache: Dict[str, Tuple[str, float]] = {}  # track_key -> (path, timestamp)
        self._cache_max_size = config.cache_size
        self._cache_ttl = config.cache_ttl_seconds

        logger.info(
            f"TrackMapper initialized: {config.postgres_host}:{config.postgres_port}, "
            f"cache_size={config.cache_size}"
        )

    def _create_engine(self) -> Engine:
        """Create SQLAlchemy engine with connection pooling.

        Returns:
            Configured SQLAlchemy Engine
        """
        engine = create_engine(
            self.config.database_url,
            poolclass=QueuePool,
            pool_size=self.config.db_pool_size,
            max_overflow=self.config.db_max_overflow,
            pool_timeout=self.config.db_pool_timeout,
            pool_recycle=self.config.db_pool_recycle,
            pool_pre_ping=True,  # Verify connections before using
            echo=self.config.debug,
        )
        logger.debug(f"Database engine created: {self.config.postgres_db}")
        return engine

    @staticmethod
    def normalize_track_key(artist: str, title: str) -> str:
        """Normalize artist and title into a consistent track key.

        Normalization:
        - Converts to lowercase
        - Strips leading/trailing whitespace
        - Format: "artist - title"

        Args:
            artist: Artist name
            title: Song title

        Returns:
            Normalized track key string

        Example:
            >>> TrackMapper.normalize_track_key("The Beatles", "Hey Jude")
            'the beatles - hey jude'
        """
        return f"{artist.strip().lower()} - {title.strip().lower()}"

    def get_loop(self, artist: str, title: str, song_id: Optional[str] = None) -> str:
        """Get video loop path for a track.

        Resolution priority:
        1. Cache lookup (if not expired)
        2. Database lookup by track key
        3. Database lookup by song ID (if provided)
        4. Default loop

        Args:
            artist: Artist name
            title: Song title
            song_id: Optional AzuraCast song ID

        Returns:
            Absolute path to MP4 loop file

        Raises:
            FileNotFoundError: If default loop doesn't exist
        """
        track_key = self.normalize_track_key(artist, title)

        # Try cache first
        cached_path = self._get_from_cache(track_key)
        if cached_path:
            logger.debug(f"Cache hit for track: {track_key}")
            if self._validate_file(cached_path):
                return cached_path
            else:
                logger.warning(f"Cached path invalid, removing: {cached_path}")
                self._remove_from_cache(track_key)

        # Try database lookup
        try:
            loop_path = self._query_loop_path(track_key, song_id)
            if loop_path and self._validate_file(loop_path):
                self._add_to_cache(track_key, loop_path)
                # Increment play count asynchronously (non-blocking)
                self._increment_play_count_async(track_key)
                return loop_path
            elif loop_path:
                logger.warning(f"Database path invalid for {track_key}: {loop_path}")
        except SQLAlchemyError as e:
            logger.error(f"Database error querying loop for {track_key}: {e}")

        # Fallback to default loop
        default_loop = self.get_default_loop()
        logger.info(f"Using default loop for {track_key}: {default_loop}")
        return default_loop

    def _query_loop_path(self, track_key: str, song_id: Optional[str] = None) -> Optional[str]:
        """Query database for loop path.

        Args:
            track_key: Normalized track key
            song_id: Optional AzuraCast song ID

        Returns:
            Loop file path if found, None otherwise
        """
        with self.engine.connect() as conn:
            # Try track key lookup
            result = conn.execute(
                text(
                    "SELECT loop_file_path FROM track_mappings "
                    "WHERE track_key = :track_key AND is_active = TRUE"
                ),
                {"track_key": track_key},
            )
            row = result.fetchone()
            if row:
                return row[0]

            # Try song ID lookup
            if song_id:
                result = conn.execute(
                    text(
                        "SELECT loop_file_path FROM track_mappings "
                        "WHERE azuracast_song_id = :song_id AND is_active = TRUE"
                    ),
                    {"song_id": song_id},
                )
                row = result.fetchone()
                if row:
                    return row[0]

        return None

    def add_mapping(
        self,
        track_key: str,
        loop_path: str,
        song_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> bool:
        """Add a new track-to-loop mapping.

        Args:
            track_key: Normalized track key
            loop_path: Absolute path to MP4 loop file
            song_id: Optional AzuraCast song ID
            notes: Optional notes/metadata

        Returns:
            True if added successfully, False if already exists

        Raises:
            ValueError: If loop file doesn't exist
            SQLAlchemyError: If database operation fails
        """
        if not self._validate_file(loop_path):
            raise ValueError(f"Loop file does not exist: {loop_path}")

        try:
            with self.engine.connect() as conn:
                conn.execute(
                    text(
                        "INSERT INTO track_mappings "
                        "(track_key, loop_file_path, azuracast_song_id, notes) "
                        "VALUES (:track_key, :loop_path, :song_id, :notes)"
                    ),
                    {
                        "track_key": track_key,
                        "loop_path": loop_path,
                        "song_id": song_id,
                        "notes": notes,
                    },
                )
                conn.commit()
            logger.info(f"Added mapping: {track_key} -> {loop_path}")
            self._add_to_cache(track_key, loop_path)
            return True
        except IntegrityError:
            logger.warning(f"Mapping already exists for: {track_key}")
            return False
        except SQLAlchemyError as e:
            logger.error(f"Error adding mapping for {track_key}: {e}")
            raise

    def update_mapping(
        self,
        track_key: str,
        loop_path: str,
        song_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> bool:
        """Update an existing track-to-loop mapping.

        Args:
            track_key: Normalized track key
            loop_path: New absolute path to MP4 loop file
            song_id: Optional new AzuraCast song ID
            notes: Optional new notes/metadata

        Returns:
            True if updated successfully, False if not found

        Raises:
            ValueError: If loop file doesn't exist
            SQLAlchemyError: If database operation fails
        """
        if not self._validate_file(loop_path):
            raise ValueError(f"Loop file does not exist: {loop_path}")

        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text(
                        "UPDATE track_mappings "
                        "SET loop_file_path = :loop_path, "
                        "    azuracast_song_id = :song_id, "
                        "    notes = :notes "
                        "WHERE track_key = :track_key AND is_active = TRUE"
                    ),
                    {
                        "track_key": track_key,
                        "loop_path": loop_path,
                        "song_id": song_id,
                        "notes": notes,
                    },
                )
                conn.commit()

                if result.rowcount > 0:
                    logger.info(f"Updated mapping: {track_key} -> {loop_path}")
                    self._add_to_cache(track_key, loop_path)
                    return True
                else:
                    logger.warning(f"No mapping found to update: {track_key}")
                    return False
        except SQLAlchemyError as e:
            logger.error(f"Error updating mapping for {track_key}: {e}")
            raise

    def delete_mapping(self, track_key: str) -> bool:
        """Soft delete a track mapping (sets is_active=FALSE).

        Args:
            track_key: Normalized track key

        Returns:
            True if deleted, False if not found
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text(
                        "UPDATE track_mappings "
                        "SET is_active = FALSE "
                        "WHERE track_key = :track_key AND is_active = TRUE"
                    ),
                    {"track_key": track_key},
                )
                conn.commit()

                if result.rowcount > 0:
                    logger.info(f"Deleted mapping: {track_key}")
                    self._remove_from_cache(track_key)
                    return True
                else:
                    logger.warning(f"No mapping found to delete: {track_key}")
                    return False
        except SQLAlchemyError as e:
            logger.error(f"Error deleting mapping for {track_key}: {e}")
            raise

    def increment_play_count(self, track_key: str) -> None:
        """Increment play count for a track (synchronous).

        Args:
            track_key: Normalized track key
        """
        try:
            with self.engine.connect() as conn:
                conn.execute(
                    text(
                        "UPDATE track_mappings "
                        "SET play_count = play_count + 1, "
                        "    last_played_at = NOW() "
                        "WHERE track_key = :track_key AND is_active = TRUE"
                    ),
                    {"track_key": track_key},
                )
                conn.commit()
            logger.debug(f"Incremented play count for: {track_key}")
        except SQLAlchemyError as e:
            logger.error(f"Error incrementing play count for {track_key}: {e}")

    def _increment_play_count_async(self, track_key: str) -> None:
        """Increment play count asynchronously (non-blocking).

        This is a simplified version. In production, use a task queue
        (Celery, RQ) or async worker.

        Args:
            track_key: Normalized track key
        """
        # For now, just call synchronous version
        # TODO: Implement async worker or task queue
        try:
            self.increment_play_count(track_key)
        except Exception as e:
            logger.error(f"Async play count increment failed: {e}")

    def get_default_loop(self) -> str:
        """Get default loop path from database or config.

        Returns:
            Path to default loop file

        Raises:
            FileNotFoundError: If default loop doesn't exist
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("SELECT value FROM default_config WHERE key = 'default_loop'")
                )
                row = result.fetchone()
                if row:
                    default_path = row[0]
                else:
                    default_path = self.config.default_loop
        except SQLAlchemyError as e:
            logger.error(f"Error querying default loop: {e}")
            default_path = self.config.default_loop

        if not self._validate_file(default_path):
            raise FileNotFoundError(f"Default loop file not found: {default_path}")

        return default_path

    def get_stats(self) -> Dict[str, Any]:
        """Get track mapping statistics.

        Returns:
            Dictionary with statistics:
            - total_tracks: Total number of mappings
            - active_tracks: Number of active mappings
            - total_plays: Sum of all play counts
            - avg_plays_per_track: Average plays per track
            - most_played_track: Track key of most played track
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT * FROM get_track_stats()"))
                row = result.fetchone()
                if row:
                    return {
                        "total_tracks": row[0] or 0,
                        "active_tracks": row[1] or 0,
                        "total_plays": row[2] or 0,
                        "avg_plays_per_track": float(row[3]) if row[3] else 0.0,
                        "most_played_track": row[4] or "N/A",
                    }
        except SQLAlchemyError as e:
            logger.error(f"Error getting stats: {e}")

        return {
            "total_tracks": 0,
            "active_tracks": 0,
            "total_plays": 0,
            "avg_plays_per_track": 0.0,
            "most_played_track": "N/A",
        }

    def get_all_mappings(
        self, active_only: bool = True, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get all track mappings.

        Args:
            active_only: Only return active mappings (default: True)
            limit: Maximum number of results (default: None = all)

        Returns:
            List of mapping dictionaries
        """
        try:
            query = "SELECT * FROM track_mappings"
            if active_only:
                query += " WHERE is_active = TRUE"
            query += " ORDER BY play_count DESC"
            if limit:
                query += f" LIMIT {limit}"

            with self.engine.connect() as conn:
                result = conn.execute(text(query))
                mappings = []
                for row in result:
                    mappings.append(
                        {
                            "id": row[0],
                            "track_key": row[1],
                            "azuracast_song_id": row[2],
                            "loop_file_path": row[3],
                            "created_at": row[4],
                            "updated_at": row[5],
                            "play_count": row[6],
                            "last_played_at": row[7],
                            "is_active": row[8],
                            "notes": row[9],
                        }
                    )
                return mappings
        except SQLAlchemyError as e:
            logger.error(f"Error getting all mappings: {e}")
            return []

    # Cache management methods

    def _get_from_cache(self, track_key: str) -> Optional[str]:
        """Get loop path from cache if not expired.

        Args:
            track_key: Normalized track key

        Returns:
            Loop path if in cache and not expired, None otherwise
        """
        if track_key in self._cache:
            path, timestamp = self._cache[track_key]
            age = datetime.now().timestamp() - timestamp
            if age < self._cache_ttl:
                return path
            else:
                # Expired, remove from cache
                del self._cache[track_key]
        return None

    def _add_to_cache(self, track_key: str, loop_path: str) -> None:
        """Add loop path to cache with timestamp.

        Implements simple LRU eviction when cache is full.

        Args:
            track_key: Normalized track key
            loop_path: Loop file path
        """
        # Evict oldest entry if cache is full
        if len(self._cache) >= self._cache_max_size:
            oldest_key = min(self._cache, key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]

        self._cache[track_key] = (loop_path, datetime.now().timestamp())

    def _remove_from_cache(self, track_key: str) -> None:
        """Remove entry from cache.

        Args:
            track_key: Normalized track key
        """
        if track_key in self._cache:
            del self._cache[track_key]

    def clear_cache(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
        logger.info("Cache cleared")

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics.

        Returns:
            Dictionary with cache size and max size
        """
        return {
            "size": len(self._cache),
            "max_size": self._cache_max_size,
            "ttl_seconds": self._cache_ttl,
        }

    @staticmethod
    def _validate_file(file_path: str) -> bool:
        """Validate that file exists and is readable.

        Args:
            file_path: Path to file

        Returns:
            True if file exists and is readable, False otherwise
        """
        try:
            return os.path.isfile(file_path) and os.access(file_path, os.R_OK)
        except Exception:
            return False

    def close(self) -> None:
        """Close database connections."""
        if self.engine:
            self.engine.dispose()
            logger.info("TrackMapper closed")

    def __enter__(self) -> "TrackMapper":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()

    def __repr__(self) -> str:
        """String representation."""
        return f"TrackMapper(db={self.config.postgres_db}, cache={len(self._cache)})"
