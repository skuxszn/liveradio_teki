"""Analytics - Query functions for track play history and system metrics.

This module provides analytics queries for reporting and analysis of
the 24/7 radio stream system.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

from sqlalchemy import create_engine, text, Engine
from sqlalchemy.exc import SQLAlchemyError

from logging_module.config import LoggingConfig


class Analytics:
    """Analytics query engine for radio stream data.

    Provides pre-built queries for common analytics tasks including:
    - Play statistics over time periods
    - Most played tracks
    - Error analysis
    - Uptime calculations
    - Hourly distribution

    Example:
        >>> config = LoggingConfig.from_env()
        >>> analytics = Analytics(config)
        >>> stats = analytics.get_play_stats(days=7)
        >>> print(f"Uptime: {stats['uptime_percent']:.2f}%")
    """

    def __init__(self, config: LoggingConfig):
        """Initialize Analytics with configuration.

        Args:
            config: LoggingConfig instance with database settings

        Raises:
            ValueError: If configuration is invalid
        """
        config.validate()
        self.config = config
        self.engine: Engine = create_engine(
            config.database_url,
            pool_pre_ping=True,
            echo=config.debug
        )

    def get_play_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        days: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get aggregate play statistics for a date range.

        Args:
            start_date: Start of date range (optional)
            end_date: End of date range (optional)
            days: Number of days back from now (overrides start_date)

        Returns:
            Dictionary with statistics:
                - total_plays: Total number of plays
                - unique_tracks: Number of unique tracks
                - total_duration_hours: Total play time in hours
                - avg_duration_seconds: Average track duration
                - error_rate: Percentage of plays with errors
                - uptime_percent: Percentage of successful plays

        Example:
            >>> stats = analytics.get_play_stats(days=7)
            >>> print(f"Total plays: {stats['total_plays']}")
        """
        if days is not None:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
        elif start_date is None:
            start_date = datetime.now() - timedelta(days=7)
        if end_date is None:
            end_date = datetime.now()

        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("SELECT * FROM get_play_stats(:start_date, :end_date)"),
                    {"start_date": start_date, "end_date": end_date}
                )
                row = result.fetchone()

                if row:
                    return {
                        "total_plays": int(row[0] or 0),
                        "unique_tracks": int(row[1] or 0),
                        "total_duration_hours": float(row[2] or 0),
                        "avg_duration_seconds": float(row[3] or 0),
                        "error_rate": float(row[4] or 0),
                        "uptime_percent": float(row[5] or 0),
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat()
                    }

                return {
                    "total_plays": 0,
                    "unique_tracks": 0,
                    "total_duration_hours": 0.0,
                    "avg_duration_seconds": 0.0,
                    "error_rate": 0.0,
                    "uptime_percent": 0.0,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                }

        except SQLAlchemyError as e:
            raise RuntimeError(f"Database error getting play stats: {e}") from e

    def get_most_played_tracks(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        days: Optional[int] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get most played tracks for a date range.

        Args:
            start_date: Start of date range (optional)
            end_date: End of date range (optional)
            days: Number of days back from now (overrides start_date)
            limit: Maximum number of tracks to return (default: 10)

        Returns:
            List of track dictionaries with play counts and statistics

        Example:
            >>> tracks = analytics.get_most_played_tracks(days=7, limit=5)
            >>> for track in tracks:
            ...     print(f"{track['artist']} - {track['title']}: {track['play_count']}")
        """
        if days is not None:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
        elif start_date is None:
            start_date = datetime.now() - timedelta(days=7)
        if end_date is None:
            end_date = datetime.now()

        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT * FROM get_most_played_tracks(
                            :start_date, :end_date, :limit_count
                        )
                    """),
                    {
                        "start_date": start_date,
                        "end_date": end_date,
                        "limit_count": limit
                    }
                )

                tracks = []
                for row in result:
                    tracks.append({
                        "track_key": row[0],
                        "artist": row[1],
                        "title": row[2],
                        "play_count": int(row[3]),
                        "total_duration_hours": float(row[4] or 0),
                        "error_count": int(row[5] or 0)
                    })

                return tracks

        except SQLAlchemyError as e:
            raise RuntimeError(f"Database error getting most played tracks: {e}") from e

    def get_error_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        days: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get error summary grouped by service and severity.

        Args:
            start_date: Start of date range (optional)
            end_date: End of date range (optional)
            days: Number of days back from now (overrides start_date)

        Returns:
            List of error summary dictionaries

        Example:
            >>> errors = analytics.get_error_summary(days=7)
            >>> for error in errors:
            ...     print(f"{error['service']}/{error['severity']}: {error['error_count']}")
        """
        if days is not None:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
        elif start_date is None:
            start_date = datetime.now() - timedelta(days=7)
        if end_date is None:
            end_date = datetime.now()

        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("SELECT * FROM get_error_summary(:start_date, :end_date)"),
                    {"start_date": start_date, "end_date": end_date}
                )

                errors = []
                for row in result:
                    errors.append({
                        "service": row[0],
                        "severity": row[1],
                        "error_count": int(row[2]),
                        "resolved_count": int(row[3]),
                        "unresolved_count": int(row[4])
                    })

                return errors

        except SQLAlchemyError as e:
            raise RuntimeError(f"Database error getting error summary: {e}") from e

    def get_hourly_play_distribution(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        days: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get play distribution by hour of day.

        Args:
            start_date: Start of date range (optional)
            end_date: End of date range (optional)
            days: Number of days back from now (overrides start_date)

        Returns:
            List of hourly distribution dictionaries (0-23 hours)

        Example:
            >>> distribution = analytics.get_hourly_play_distribution(days=7)
            >>> for hour in distribution:
            ...     print(f"Hour {hour['hour_of_day']}: {hour['play_count']} plays")
        """
        if days is not None:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
        elif start_date is None:
            start_date = datetime.now() - timedelta(days=7)
        if end_date is None:
            end_date = datetime.now()

        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT * FROM get_hourly_play_distribution(
                            :start_date, :end_date
                        )
                    """),
                    {"start_date": start_date, "end_date": end_date}
                )

                distribution = []
                for row in result:
                    distribution.append({
                        "hour_of_day": int(row[0]),
                        "play_count": int(row[1]),
                        "avg_duration_seconds": float(row[2] or 0)
                    })

                return distribution

        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Database error getting hourly distribution: {e}"
            ) from e

    def get_daily_summary(
        self,
        date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get daily summary for a specific date.

        Args:
            date: Date to summarize (default: yesterday)

        Returns:
            Dictionary with daily summary statistics

        Example:
            >>> summary = analytics.get_daily_summary()
            >>> print(f"Yesterday: {summary['total_plays']} plays, "
            ...       f"{summary['uptime_percent']:.2f}% uptime")
        """
        if date is None:
            date = datetime.now() - timedelta(days=1)

        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)

        stats = self.get_play_stats(start_date=start_date, end_date=end_date)
        most_played = self.get_most_played_tracks(
            start_date=start_date,
            end_date=end_date,
            limit=5
        )
        errors = self.get_error_summary(start_date=start_date, end_date=end_date)

        return {
            "date": start_date.date().isoformat(),
            "total_plays": stats["total_plays"],
            "unique_tracks": stats["unique_tracks"],
            "total_duration_hours": stats["total_duration_hours"],
            "uptime_percent": stats["uptime_percent"],
            "error_rate": stats["error_rate"],
            "most_played_tracks": most_played,
            "error_summary": errors
        }

    def get_weekly_summary(
        self,
        week_start: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get weekly summary starting from a specific date.

        Args:
            week_start: Start of week (default: 7 days ago)

        Returns:
            Dictionary with weekly summary statistics

        Example:
            >>> summary = analytics.get_weekly_summary()
            >>> print(f"This week: {summary['total_plays']} plays")
        """
        if week_start is None:
            week_start = datetime.now() - timedelta(days=7)

        end_date = week_start + timedelta(days=7)

        stats = self.get_play_stats(start_date=week_start, end_date=end_date)
        most_played = self.get_most_played_tracks(
            start_date=week_start,
            end_date=end_date,
            limit=10
        )
        errors = self.get_error_summary(start_date=week_start, end_date=end_date)
        hourly = self.get_hourly_play_distribution(
            start_date=week_start,
            end_date=end_date
        )

        return {
            "week_start": week_start.date().isoformat(),
            "week_end": end_date.date().isoformat(),
            "total_plays": stats["total_plays"],
            "unique_tracks": stats["unique_tracks"],
            "total_duration_hours": stats["total_duration_hours"],
            "uptime_percent": stats["uptime_percent"],
            "error_rate": stats["error_rate"],
            "most_played_tracks": most_played,
            "error_summary": errors,
            "hourly_distribution": hourly
        }

    def get_track_history(
        self,
        artist: str,
        title: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get play history for a specific track.

        Args:
            artist: Artist name
            title: Song title
            limit: Maximum number of records to return (default: 50)

        Returns:
            List of play history records for the track

        Example:
            >>> history = analytics.get_track_history("The Beatles", "Hey Jude")
            >>> print(f"Played {len(history)} times")
        """
        track_key = f"{artist.strip().lower()} - {title.strip().lower()}"

        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT
                            id, started_at, ended_at, duration_seconds,
                            had_errors, error_message, ffmpeg_pid,
                            loop_file_path
                        FROM play_history
                        WHERE track_key = :track_key
                        ORDER BY started_at DESC
                        LIMIT :limit
                    """),
                    {"track_key": track_key, "limit": limit}
                )

                history = []
                for row in result:
                    history.append({
                        "id": row[0],
                        "started_at": row[1].isoformat() if row[1] else None,
                        "ended_at": row[2].isoformat() if row[2] else None,
                        "duration_seconds": row[3],
                        "had_errors": row[4],
                        "error_message": row[5],
                        "ffmpeg_pid": row[6],
                        "loop_file_path": row[7]
                    })

                return history

        except SQLAlchemyError as e:
            raise RuntimeError(f"Database error getting track history: {e}") from e

    def get_uptime_by_day(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        days: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get daily uptime percentages for a date range.

        Args:
            start_date: Start of date range (optional)
            end_date: End of date range (optional)
            days: Number of days back from now (overrides start_date)

        Returns:
            List of daily uptime records

        Example:
            >>> uptime = analytics.get_uptime_by_day(days=30)
            >>> for day in uptime:
            ...     print(f"{day['date']}: {day['uptime_percent']:.2f}%")
        """
        if days is not None:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
        elif start_date is None:
            start_date = datetime.now() - timedelta(days=7)
        if end_date is None:
            end_date = datetime.now()

        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT
                            DATE(started_at) as date,
                            COUNT(*) as total_plays,
                            COUNT(*) FILTER (WHERE had_errors = FALSE) as successful_plays,
                            (COUNT(*) FILTER (WHERE had_errors = FALSE)::NUMERIC 
                                / NULLIF(COUNT(*), 0) * 100) as uptime_percent,
                            SUM(duration_seconds) / 3600.0 as total_hours
                        FROM play_history
                        WHERE started_at >= :start_date AND started_at <= :end_date
                        GROUP BY DATE(started_at)
                        ORDER BY DATE(started_at) DESC
                    """),
                    {"start_date": start_date, "end_date": end_date}
                )

                uptime_data = []
                for row in result:
                    uptime_data.append({
                        "date": row[0].isoformat(),
                        "total_plays": int(row[1]),
                        "successful_plays": int(row[2]),
                        "uptime_percent": float(row[3] or 0),
                        "total_hours": float(row[4] or 0)
                    })

                return uptime_data

        except SQLAlchemyError as e:
            raise RuntimeError(f"Database error getting uptime by day: {e}") from e

    def get_error_timeline(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        days: Optional[int] = None,
        severity: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get error timeline for a date range.

        Args:
            start_date: Start of date range (optional)
            end_date: End of date range (optional)
            days: Number of days back from now (overrides start_date)
            severity: Filter by severity (optional)

        Returns:
            List of error records in chronological order

        Example:
            >>> errors = analytics.get_error_timeline(days=7, severity="error")
            >>> for error in errors:
            ...     print(f"{error['timestamp']}: {error['message']}")
        """
        if days is not None:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
        elif start_date is None:
            start_date = datetime.now() - timedelta(days=7)
        if end_date is None:
            end_date = datetime.now()

        try:
            with self.engine.connect() as conn:
                if severity:
                    result = conn.execute(
                        text("""
                            SELECT
                                id, timestamp, service, severity,
                                message, resolved
                            FROM error_log
                            WHERE timestamp >= :start_date 
                              AND timestamp <= :end_date
                              AND severity = :severity
                            ORDER BY timestamp DESC
                        """),
                        {
                            "start_date": start_date,
                            "end_date": end_date,
                            "severity": severity.lower()
                        }
                    )
                else:
                    result = conn.execute(
                        text("""
                            SELECT
                                id, timestamp, service, severity,
                                message, resolved
                            FROM error_log
                            WHERE timestamp >= :start_date 
                              AND timestamp <= :end_date
                            ORDER BY timestamp DESC
                        """),
                        {"start_date": start_date, "end_date": end_date}
                    )

                errors = []
                for row in result:
                    errors.append({
                        "id": row[0],
                        "timestamp": row[1].isoformat() if row[1] else None,
                        "service": row[2],
                        "severity": row[3],
                        "message": row[4],
                        "resolved": row[5]
                    })

                return errors

        except SQLAlchemyError as e:
            raise RuntimeError(f"Database error getting error timeline: {e}") from e

    def close(self) -> None:
        """Close database connection.

        Example:
            >>> analytics.close()
        """
        try:
            self.engine.dispose()
        except Exception:
            pass

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()



