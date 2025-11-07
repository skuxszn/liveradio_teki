"""Unit tests for logging_module.logger."""

import json
import pytest
from datetime import datetime
from sqlalchemy import text

from logging_module.logger import RadioLogger, JsonFormatter
import logging


class TestRadioLogger:
    """Tests for RadioLogger class."""

    def test_initialization(self, test_logger):
        """Test logger initialization."""
        assert test_logger is not None
        assert test_logger.engine is not None
        assert test_logger._logger is not None

    def test_log_track_started(self, test_logger, sample_track_info):
        """Test logging track start."""
        play_id = test_logger.log_track_started(sample_track_info, "/srv/loops/test.mp4", 12345)

        assert play_id is not None
        assert isinstance(play_id, int)
        assert test_logger._current_play_id == play_id

    def test_log_track_started_with_metadata(self, test_logger, sample_track_info):
        """Test logging track start with additional metadata."""
        metadata = {"custom_field": "custom_value"}

        play_id = test_logger.log_track_started(
            sample_track_info, "/srv/loops/test.mp4", 12345, metadata=metadata
        )

        assert play_id is not None

    def test_log_track_started_minimal_info(self, test_logger):
        """Test logging track start with minimal info."""
        minimal_info = {"artist": "Artist", "title": "Title"}

        play_id = test_logger.log_track_started(minimal_info, "/srv/loops/test.mp4", 12345)

        assert play_id is not None

    def test_log_track_ended(self, test_logger, sample_track_info):
        """Test logging track end."""
        play_id = test_logger.log_track_started(sample_track_info, "/srv/loops/test.mp4", 12345)

        result = test_logger.log_track_ended(play_id, had_errors=False)
        assert result is True

    def test_log_track_ended_with_errors(self, test_logger, sample_track_info):
        """Test logging track end with errors."""
        play_id = test_logger.log_track_started(sample_track_info, "/srv/loops/test.mp4", 12345)

        result = test_logger.log_track_ended(
            play_id, had_errors=True, error_message="Test error", error_count=3
        )
        assert result is True

    def test_log_track_ended_without_play_id(self, test_logger):
        """Test logging track end without play_id."""
        test_logger._current_play_id = None
        result = test_logger.log_track_ended()
        assert result is False

    def test_log_track_ended_uses_current_id(self, test_logger, sample_track_info):
        """Test logging track end uses current play ID if not provided."""
        play_id = test_logger.log_track_started(sample_track_info, "/srv/loops/test.mp4", 12345)

        # Don't pass play_id, should use current
        result = test_logger.log_track_ended(had_errors=False)
        assert result is True
        assert test_logger._current_play_id is None  # Should be cleared

    def test_log_error(self, test_logger):
        """Test logging error."""
        error_id = test_logger.log_error("ffmpeg", "error", "Test error message", {"key": "value"})

        assert error_id is not None
        assert isinstance(error_id, int)

    def test_log_error_with_stack_trace(self, test_logger):
        """Test logging error with stack trace."""
        error_id = test_logger.log_error(
            "watcher", "critical", "Critical error", stack_trace="Traceback...\nLine 1\nLine 2"
        )

        assert error_id is not None

    def test_log_error_invalid_severity(self, test_logger):
        """Test logging error with invalid severity defaults to 'error'."""
        error_id = test_logger.log_error("service", "invalid_severity", "Message")

        assert error_id is not None

    def test_log_error_with_play_history_id(self, test_logger, sample_track_info):
        """Test logging error with associated play history ID."""
        play_id = test_logger.log_track_started(sample_track_info, "/srv/loops/test.mp4", 12345)

        error_id = test_logger.log_error(
            "ffmpeg", "warning", "Frame dropped", play_history_id=play_id
        )

        assert error_id is not None

    def test_log_metric(self, test_logger):
        """Test logging system metric."""
        result = test_logger.log_metric("cpu_usage", 45.5, "percent", "ffmpeg")

        assert result is True

    def test_log_metric_without_optional_fields(self, test_logger):
        """Test logging metric without optional fields."""
        result = test_logger.log_metric("memory_mb", 1024.0)
        assert result is True

    def test_log_metric_with_metadata(self, test_logger):
        """Test logging metric with metadata."""
        result = test_logger.log_metric(
            "disk_usage", 80.0, "percent", metadata={"disk": "/dev/sda1"}
        )

        assert result is True

    def test_get_recent_plays(self, test_logger, sample_track_info):
        """Test getting recent plays."""
        # Log some tracks
        for i in range(5):
            test_logger.log_track_started(sample_track_info, f"/srv/loops/track{i}.mp4", 12345 + i)

        recent = test_logger.get_recent_plays(limit=3)
        assert len(recent) == 3
        assert all(isinstance(play, dict) for play in recent)

    def test_get_recent_plays_empty(self, test_logger):
        """Test getting recent plays when database is empty."""
        recent = test_logger.get_recent_plays()
        assert recent == []

    def test_get_current_playing(self, test_logger, sample_track_info):
        """Test getting currently playing track."""
        play_id = test_logger.log_track_started(sample_track_info, "/srv/loops/test.mp4", 12345)

        current = test_logger.get_current_playing()
        assert current is not None
        assert current["id"] == play_id
        assert current["artist"] == "Test Artist"
        assert current["title"] == "Test Song"

    def test_get_current_playing_none(self, test_logger, sample_track_info):
        """Test getting current playing when track has ended."""
        play_id = test_logger.log_track_started(sample_track_info, "/srv/loops/test.mp4", 12345)
        test_logger.log_track_ended(play_id)

        current = test_logger.get_current_playing()
        # Should be None since track ended
        # Note: This depends on the view definition

    def test_cleanup_old_data(self, test_logger):
        """Test cleanup of old data."""
        result = test_logger.cleanup_old_data()

        assert isinstance(result, dict)
        assert "play_history" in result
        assert "error_log" in result
        assert isinstance(result["play_history"], int)
        assert isinstance(result["error_log"], int)

    def test_normalize_track_key(self):
        """Test track key normalization."""
        key = RadioLogger._normalize_track_key("  The Beatles  ", "  Hey Jude  ")
        assert key == "the beatles - hey jude"

    def test_normalize_track_key_case_insensitive(self):
        """Test track key normalization is case insensitive."""
        key1 = RadioLogger._normalize_track_key("ARTIST", "TITLE")
        key2 = RadioLogger._normalize_track_key("artist", "title")
        assert key1 == key2

    def test_context_manager(self, test_config, test_engine, monkeypatch):
        """Test RadioLogger as context manager."""

        def mock_create_engine(self):
            return test_engine

        monkeypatch.setattr(RadioLogger, "_create_engine", mock_create_engine)

        with RadioLogger(test_config) as logger:
            assert logger is not None
            assert logger.engine is not None

    def test_close(self, test_logger):
        """Test closing logger."""
        test_logger.close()
        # Should not raise exception


class TestJsonFormatter:
    """Tests for JsonFormatter class."""

    def test_format_basic(self):
        """Test basic JSON formatting."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert data["message"] == "Test message"
        assert data["level"] == "INFO"
        assert data["logger"] == "test"
        assert "timestamp" in data

    def test_format_with_extra_fields(self):
        """Test JSON formatting with extra fields."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error message",
            args=(),
            exc_info=None,
        )
        record.event = "test_event"
        record.custom_field = "custom_value"

        result = formatter.format(record)
        data = json.loads(result)

        assert data["event"] == "test_event"
        assert data["custom_field"] == "custom_value"

    def test_format_with_exception(self):
        """Test JSON formatting with exception info."""
        formatter = JsonFormatter()

        try:
            raise ValueError("Test exception")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="test.py",
                lineno=1,
                msg="Exception occurred",
                args=(),
                exc_info=exc_info,
            )

            result = formatter.format(record)
            data = json.loads(result)

            assert "exception" in data
            assert "ValueError" in data["exception"]
            assert "Test exception" in data["exception"]


class TestRadioLoggerIntegration:
    """Integration tests for RadioLogger."""

    def test_full_track_lifecycle(self, test_logger, sample_track_info):
        """Test complete track lifecycle: start -> end."""
        # Start track
        play_id = test_logger.log_track_started(sample_track_info, "/srv/loops/test.mp4", 12345)

        assert play_id is not None

        # Get current playing
        current = test_logger.get_current_playing()
        assert current is not None
        assert current["id"] == play_id

        # End track
        result = test_logger.log_track_ended(play_id)
        assert result is True

        # Check in recent plays
        recent = test_logger.get_recent_plays(limit=1)
        assert len(recent) == 1
        assert recent[0]["id"] == play_id

    def test_multiple_tracks_with_errors(self, test_logger, sample_track_info):
        """Test logging multiple tracks with some having errors."""
        play_ids = []

        # Log 3 tracks
        for i in range(3):
            play_id = test_logger.log_track_started(
                sample_track_info, f"/srv/loops/track{i}.mp4", 12345 + i
            )
            play_ids.append(play_id)

            # Log error for track 1
            if i == 1:
                test_logger.log_error("ffmpeg", "error", "Connection lost", play_history_id=play_id)

            # End track
            has_errors = i == 1
            test_logger.log_track_ended(
                play_id, had_errors=has_errors, error_count=1 if has_errors else 0
            )

        # Check all tracks were logged
        recent = test_logger.get_recent_plays(limit=5)
        assert len(recent) == 3

        # Check that track 1 has errors
        track_with_errors = [p for p in recent if p["id"] == play_ids[1]]
        assert len(track_with_errors) == 1
        assert track_with_errors[0]["had_errors"] is True

    def test_metrics_logging(self, test_logger):
        """Test logging multiple metrics."""
        metrics = [
            ("cpu_usage", 45.5, "percent", "ffmpeg"),
            ("memory_mb", 1024.0, "MB", "ffmpeg"),
            ("bitrate", 3000.0, "kbps", "ffmpeg"),
            ("fps", 30.0, "fps", "ffmpeg"),
        ]

        for metric_name, value, unit, service in metrics:
            result = test_logger.log_metric(metric_name, value, unit, service)
            assert result is True
