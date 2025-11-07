"""Logger - Track play history and error logging with database integration.

This module provides comprehensive logging for the 24/7 radio stream system,
including track play history, error tracking, and system metrics.
"""

import json
import logging
import os
import sys
import traceback
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from typing import Optional, Dict, Any, List

from sqlalchemy import create_engine, text, Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import QueuePool

from logging_module.config import LoggingConfig


class RadioLogger:
    """Comprehensive logging system for 24/7 radio stream.

    Features:
    - Track play history logging to database
    - Error logging with severity levels
    - System metrics tracking
    - Structured JSON logging to files
    - Rotating log file handler
    - Database integration with connection pooling
    - Performance optimized (<10ms overhead)

    Example:
        >>> config = LoggingConfig.from_env()
        >>> logger = RadioLogger(config)
        >>> logger.log_track_started({
        ...     "artist": "The Beatles",
        ...     "title": "Hey Jude",
        ...     "album": "Hey Jude"
        ... }, "/srv/loops/track.mp4", 12345)
        >>> logger.log_error("ffmpeg", "error", "Connection failed", {"retry": 3})
    """

    def __init__(self, config: LoggingConfig):
        """Initialize RadioLogger with configuration.

        Args:
            config: LoggingConfig instance with database and logging settings

        Raises:
            ValueError: If configuration is invalid
            SQLAlchemyError: If database connection fails
        """
        config.validate()
        self.config = config
        self.engine: Engine = self._create_engine()
        self._logger = self._setup_structured_logger()
        self._current_play_id: Optional[int] = None

        self._logger.info(
            "RadioLogger initialized",
            extra={
                "database": config.postgres_db,
                "log_path": config.log_path,
                "log_level": config.log_level,
            },
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
        return engine

    def _setup_structured_logger(self) -> logging.Logger:
        """Set up structured JSON logger with rotating file handler.

        Returns:
            Configured Python logger instance
        """
        logger = logging.getLogger("radio_stream")
        logger.setLevel(getattr(logging, self.config.log_level))
        logger.handlers.clear()  # Remove any existing handlers

        # Console handler (stdout)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, self.config.log_level))
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # Rotating file handler (JSON format)
        try:
            os.makedirs(self.config.log_path, exist_ok=True)
            log_file = os.path.join(self.config.log_path, "radio_stream.log")

            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=self.config.log_file_max_bytes,
                backupCount=self.config.log_file_backup_count,
            )
            file_handler.setLevel(getattr(logging, self.config.log_level))
            file_formatter = JsonFormatter()
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        except (OSError, PermissionError) as e:
            logger.warning(f"Could not create log file: {e}. Logging to console only.")

        return logger

    def log_track_started(
        self,
        track_info: Dict[str, Any],
        loop_path: str,
        ffmpeg_pid: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        """Log when a track starts playing.

        Args:
            track_info: Dictionary with track metadata (artist, title, album, etc.)
            loop_path: Path to video loop file being used
            ffmpeg_pid: FFmpeg process ID
            metadata: Additional metadata (optional)

        Returns:
            Play history ID (for later updates), or None if logging failed

        Example:
            >>> play_id = logger.log_track_started({
            ...     "artist": "Artist Name",
            ...     "title": "Song Title",
            ...     "album": "Album Name",
            ...     "azuracast_song_id": "123",
            ...     "duration": 180
            ... }, "/srv/loops/track.mp4", 12345)
        """
        try:
            artist = track_info.get("artist", "Unknown Artist")
            title = track_info.get("title", "Unknown Title")
            album = track_info.get("album")
            azuracast_song_id = track_info.get("azuracast_song_id")
            expected_duration = track_info.get("duration")

            # Normalize track key (consistent with track_mapper)
            track_key = self._normalize_track_key(artist, title)

            # Prepare metadata
            meta = metadata or {}
            meta.update({"raw_track_info": track_info, "logged_at": datetime.now().isoformat()})

            # Insert into database
            with self.engine.connect() as conn:
                result = conn.execute(
                    text(
                        """
                        INSERT INTO play_history (
                            track_key, artist, title, album, azuracast_song_id,
                            loop_file_path, started_at, expected_duration_seconds,
                            ffmpeg_pid, metadata
                        ) VALUES (
                            :track_key, :artist, :title, :album, :azuracast_song_id,
                            :loop_path, :started_at, :expected_duration,
                            :ffmpeg_pid, :metadata
                        ) RETURNING id
                    """
                    ),
                    {
                        "track_key": track_key,
                        "artist": artist,
                        "title": title,
                        "album": album,
                        "azuracast_song_id": azuracast_song_id,
                        "loop_path": loop_path,
                        "started_at": datetime.now(),
                        "expected_duration": expected_duration,
                        "ffmpeg_pid": ffmpeg_pid,
                        "metadata": json.dumps(meta),
                    },
                )
                conn.commit()
                play_id = result.fetchone()[0]

            self._current_play_id = play_id

            self._logger.info(
                "Track started",
                extra={
                    "event": "track_started",
                    "play_id": play_id,
                    "track_key": track_key,
                    "artist": artist,
                    "title": title,
                    "album": album,
                    "loop_path": loop_path,
                    "ffmpeg_pid": ffmpeg_pid,
                },
            )

            return play_id

        except SQLAlchemyError as e:
            self._logger.error(
                f"Database error logging track start: {e}",
                extra={"event": "track_start_error", "error": str(e)},
            )
            return None
        except Exception as e:
            self._logger.error(
                f"Unexpected error logging track start: {e}",
                extra={"event": "track_start_error", "error": str(e)},
            )
            return None

    def log_track_ended(
        self,
        play_id: Optional[int] = None,
        had_errors: bool = False,
        error_message: Optional[str] = None,
        error_count: int = 0,
    ) -> bool:
        """Log when a track ends playing.

        Args:
            play_id: Play history ID (uses current if not provided)
            had_errors: Whether errors occurred during playback
            error_message: Error message if applicable
            error_count: Number of errors during playback

        Returns:
            True if logging succeeded, False otherwise

        Example:
            >>> logger.log_track_ended(play_id=123, had_errors=False)
        """
        if play_id is None:
            play_id = self._current_play_id

        if play_id is None:
            self._logger.warning("Cannot end track: no play_id available")
            return False

        try:
            with self.engine.connect() as conn:
                conn.execute(
                    text(
                        """
                        UPDATE play_history
                        SET ended_at = :ended_at,
                            had_errors = :had_errors,
                            error_message = :error_message,
                            error_count = :error_count
                        WHERE id = :play_id
                    """
                    ),
                    {
                        "play_id": play_id,
                        "ended_at": datetime.now(),
                        "had_errors": had_errors,
                        "error_message": error_message,
                        "error_count": error_count,
                    },
                )
                conn.commit()

            self._logger.info(
                "Track ended",
                extra={
                    "event": "track_ended",
                    "play_id": play_id,
                    "had_errors": had_errors,
                    "error_count": error_count,
                },
            )

            if self._current_play_id == play_id:
                self._current_play_id = None

            return True

        except SQLAlchemyError as e:
            self._logger.error(
                f"Database error logging track end: {e}",
                extra={"event": "track_end_error", "error": str(e), "play_id": play_id},
            )
            return False
        except Exception as e:
            self._logger.error(
                f"Unexpected error logging track end: {e}",
                extra={"event": "track_end_error", "error": str(e), "play_id": play_id},
            )
            return False

    def log_error(
        self,
        service: str,
        severity: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        stack_trace: Optional[str] = None,
        play_history_id: Optional[int] = None,
    ) -> Optional[int]:
        """Log an error to the database and log file.

        Args:
            service: Service name (e.g., 'ffmpeg', 'watcher', 'rtmp')
            severity: Error severity ('info', 'warning', 'error', 'critical')
            message: Error message
            context: Additional context data (optional)
            stack_trace: Stack trace string (optional)
            play_history_id: Associated play history ID (optional)

        Returns:
            Error log ID, or None if logging failed

        Example:
            >>> logger.log_error(
            ...     "ffmpeg",
            ...     "error",
            ...     "Connection refused",
            ...     {"host": "localhost", "port": 1935}
            ... )
        """
        try:
            # Validate severity
            valid_severities = ["info", "warning", "error", "critical"]
            if severity.lower() not in valid_severities:
                severity = "error"

            # Insert into database
            with self.engine.connect() as conn:
                result = conn.execute(
                    text(
                        """
                        INSERT INTO error_log (
                            timestamp, service, severity, message,
                            context, stack_trace, play_history_id
                        ) VALUES (
                            :timestamp, :service, :severity, :message,
                            :context, :stack_trace, :play_history_id
                        ) RETURNING id
                    """
                    ),
                    {
                        "timestamp": datetime.now(),
                        "service": service,
                        "severity": severity.lower(),
                        "message": message,
                        "context": json.dumps(context) if context else None,
                        "stack_trace": stack_trace,
                        "play_history_id": play_history_id or self._current_play_id,
                    },
                )
                conn.commit()
                error_id = result.fetchone()[0]

            # Also log to structured logger
            log_level = getattr(logging, severity.upper(), logging.ERROR)
            self._logger.log(
                log_level,
                message,
                extra={
                    "event": "error_logged",
                    "error_id": error_id,
                    "service": service,
                    "severity": severity,
                    "context": context,
                },
            )

            return error_id

        except SQLAlchemyError as e:
            self._logger.error(
                f"Database error logging error: {e}",
                extra={"event": "log_error_error", "error": str(e)},
            )
            return None
        except Exception as e:
            self._logger.error(
                f"Unexpected error logging error: {e}",
                extra={"event": "log_error_error", "error": str(e)},
            )
            return None

    def log_metric(
        self,
        metric_name: str,
        metric_value: float,
        unit: Optional[str] = None,
        service: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Log a system metric to the database.

        Args:
            metric_name: Name of the metric (e.g., 'cpu_usage', 'memory_mb')
            metric_value: Numeric value of the metric
            unit: Unit of measurement (e.g., 'percent', 'MB', 'seconds')
            service: Service name (optional)
            metadata: Additional metadata (optional)

        Returns:
            True if logging succeeded, False otherwise

        Example:
            >>> logger.log_metric("cpu_usage", 45.2, "percent", "ffmpeg")
        """
        try:
            with self.engine.connect() as conn:
                conn.execute(
                    text(
                        """
                        INSERT INTO system_metrics (
                            timestamp, metric_name, metric_value,
                            unit, service, metadata
                        ) VALUES (
                            :timestamp, :metric_name, :metric_value,
                            :unit, :service, :metadata
                        )
                    """
                    ),
                    {
                        "timestamp": datetime.now(),
                        "metric_name": metric_name,
                        "metric_value": metric_value,
                        "unit": unit,
                        "service": service,
                        "metadata": json.dumps(metadata) if metadata else None,
                    },
                )
                conn.commit()

            return True

        except SQLAlchemyError as e:
            self._logger.error(
                f"Database error logging metric: {e}",
                extra={"event": "metric_error", "error": str(e)},
            )
            return False
        except Exception as e:
            self._logger.error(
                f"Unexpected error logging metric: {e}",
                extra={"event": "metric_error", "error": str(e)},
            )
            return False

    def get_recent_plays(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent play history records.

        Args:
            limit: Maximum number of records to return (default: 50)

        Returns:
            List of play history dictionaries

        Example:
            >>> recent = logger.get_recent_plays(10)
            >>> for play in recent:
            ...     print(f"{play['artist']} - {play['title']}")
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text(
                        """
                        SELECT
                            id, track_key, artist, title, album,
                            azuracast_song_id, loop_file_path,
                            started_at, ended_at, duration_seconds,
                            expected_duration_seconds, ffmpeg_pid,
                            had_errors, error_message, error_count
                        FROM play_history
                        ORDER BY started_at DESC
                        LIMIT :limit
                    """
                    ),
                    {"limit": limit},
                )

                plays = []
                for row in result:
                    plays.append(
                        {
                            "id": row[0],
                            "track_key": row[1],
                            "artist": row[2],
                            "title": row[3],
                            "album": row[4],
                            "azuracast_song_id": row[5],
                            "loop_file_path": row[6],
                            "started_at": row[7].isoformat() if row[7] else None,
                            "ended_at": row[8].isoformat() if row[8] else None,
                            "duration_seconds": row[9],
                            "expected_duration_seconds": row[10],
                            "ffmpeg_pid": row[11],
                            "had_errors": row[12],
                            "error_message": row[13],
                            "error_count": row[14],
                        }
                    )

                return plays

        except SQLAlchemyError as e:
            self._logger.error(f"Database error getting recent plays: {e}")
            return []
        except Exception as e:
            self._logger.error(f"Unexpected error getting recent plays: {e}")
            return []

    def get_current_playing(self) -> Optional[Dict[str, Any]]:
        """Get currently playing track information.

        Returns:
            Dictionary with current track info, or None if nothing is playing

        Example:
            >>> current = logger.get_current_playing()
            >>> if current:
            ...     print(f"Now playing: {current['artist']} - {current['title']}")
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text(
                        """
                        SELECT * FROM current_playing
                    """
                    )
                )
                row = result.fetchone()

                if row:
                    return {
                        "id": row[0],
                        "track_key": row[1],
                        "artist": row[2],
                        "title": row[3],
                        "album": row[4],
                        "loop_file_path": row[5],
                        "started_at": row[6].isoformat() if row[6] else None,
                        "ffmpeg_pid": row[7],
                        "elapsed_seconds": row[8],
                    }

                return None

        except SQLAlchemyError as e:
            self._logger.error(f"Database error getting current playing: {e}")
            return None
        except Exception as e:
            self._logger.error(f"Unexpected error getting current playing: {e}")
            return None

    def cleanup_old_data(self) -> Dict[str, int]:
        """Clean up old data based on retention policies.

        Returns:
            Dictionary with counts of deleted records

        Example:
            >>> result = logger.cleanup_old_data()
            >>> print(f"Deleted {result['play_history']} old play records")
        """
        try:
            deleted = {"play_history": 0, "error_log": 0}

            with self.engine.connect() as conn:
                # Clean old play history
                result = conn.execute(
                    text("SELECT archive_old_play_history(:days)"),
                    {"days": self.config.play_history_retention_days},
                )
                deleted["play_history"] = result.fetchone()[0]

                # Clean resolved errors
                result = conn.execute(
                    text("SELECT clean_resolved_errors(:days)"),
                    {"days": self.config.error_log_retention_days},
                )
                deleted["error_log"] = result.fetchone()[0]

                conn.commit()

            self._logger.info(
                "Old data cleaned",
                extra={
                    "event": "cleanup",
                    "play_history_deleted": deleted["play_history"],
                    "error_log_deleted": deleted["error_log"],
                },
            )

            return deleted

        except SQLAlchemyError as e:
            self._logger.error(f"Database error cleaning old data: {e}")
            return {"play_history": 0, "error_log": 0}
        except Exception as e:
            self._logger.error(f"Unexpected error cleaning old data: {e}")
            return {"play_history": 0, "error_log": 0}

    @staticmethod
    def _normalize_track_key(artist: str, title: str) -> str:
        """Normalize artist and title into a consistent track key.

        Args:
            artist: Artist name
            title: Song title

        Returns:
            Normalized track key string

        Example:
            >>> RadioLogger._normalize_track_key("The Beatles", "Hey Jude")
            'the beatles - hey jude'
        """
        return f"{artist.strip().lower()} - {title.strip().lower()}"

    def close(self) -> None:
        """Close database connection and cleanup resources.

        Example:
            >>> logger.close()
        """
        try:
            self.engine.dispose()
            self._logger.info("RadioLogger closed")
        except Exception as e:
            self._logger.error(f"Error closing RadioLogger: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


class JsonFormatter(logging.Formatter):
    """JSON log formatter for structured logging.

    Formats log records as JSON with timestamp, level, message, and extra fields.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON-formatted string
        """
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields
        if hasattr(record, "event"):
            log_data["event"] = record.event

        # Add all custom extra fields
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
            ]:
                log_data[key] = value

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)
