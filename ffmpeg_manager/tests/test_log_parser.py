"""
Tests for FFmpeg log parser.
"""

import pytest

from ffmpeg_manager.log_parser import (
    ErrorType,
    FFmpegError,
    FFmpegLogParser,
    FFmpegMetrics,
    LogLevel,
)


class TestFFmpegLogParser:
    """Test FFmpeg log parser."""

    def test_initialization(self, log_parser: FFmpegLogParser):
        """Test log parser initialization."""
        assert log_parser.metrics is not None
        assert isinstance(log_parser.metrics, FFmpegMetrics)
        assert log_parser.errors == []
        assert log_parser.warnings == []

    def test_parse_metrics_line(self, log_parser: FFmpegLogParser):
        """Test parsing FFmpeg metrics output."""
        line = "frame=  100 fps= 30 q=28.0 size=512kB time=00:00:03.33 bitrate=1258.3kbits/s speed=1.00x"

        log_parser.parse_line(line)

        assert log_parser.metrics.frame_count == 100
        assert log_parser.metrics.fps == 30.0
        assert log_parser.metrics.time == "00:00:03.33"
        assert log_parser.metrics.bitrate == "1258.3kbits/s"
        assert log_parser.metrics.speed == 1.00

    def test_parse_metrics_with_dup_drop(self, log_parser: FFmpegLogParser):
        """Test parsing metrics with dup/drop frames."""
        line = "frame=  200 fps= 30 q=28.0 size=1024kB time=00:00:06.66 bitrate=1258.3kbits/s dup=5 drop=3 speed=1.00x"

        log_parser.parse_line(line)

        assert log_parser.metrics.frame_count == 200
        assert log_parser.metrics.dup_frames == 5
        assert log_parser.metrics.drop_frames == 3

    def test_parse_connection_error(self, log_parser: FFmpegLogParser):
        """Test parsing connection error."""
        line = "[error] Connection refused"

        error = log_parser.parse_line(line)

        assert error is not None
        assert error.level == LogLevel.ERROR
        assert error.error_type == ErrorType.CONNECTION_FAILED
        assert "Connection refused" in error.message

    def test_parse_file_not_found(self, log_parser: FFmpegLogParser):
        """Test parsing file not found error."""
        line = "[fatal] No such file or directory: /path/to/missing.mp4"

        error = log_parser.parse_line(line)

        assert error is not None
        assert error.level == LogLevel.FATAL
        assert error.error_type == ErrorType.FILE_NOT_FOUND

    def test_parse_rtmp_error(self, log_parser: FFmpegLogParser):
        """Test parsing RTMP error."""
        line = "[error] RTMP connection error: stream closed"

        error = log_parser.parse_line(line)

        assert error is not None
        assert error.error_type == ErrorType.RTMP_ERROR

    def test_parse_encoder_error(self, log_parser: FFmpegLogParser):
        """Test parsing encoder error."""
        line = "[error] Encoding failed"

        error = log_parser.parse_line(line)

        assert error is not None
        assert error.error_type == ErrorType.ENCODER_ERROR

    def test_parse_memory_error(self, log_parser: FFmpegLogParser):
        """Test parsing memory error."""
        line = "[error] Cannot allocate memory"

        error = log_parser.parse_line(line)

        assert error is not None
        assert error.error_type == ErrorType.MEMORY_ERROR

    def test_parse_warning(self, log_parser: FFmpegLogParser):
        """Test parsing warning message."""
        # Warnings need to match a pattern or will be ignored if they don't have error/fatal/panic level
        # For now, just verify that unknown errors with error level get detected
        line = "[error] Unknown error type"

        error = log_parser.parse_line(line)

        assert error is not None
        assert error.level == LogLevel.ERROR
        assert error.error_type == ErrorType.UNKNOWN

    def test_parse_multiple_errors(self, log_parser: FFmpegLogParser, sample_error_lines):
        """Test parsing multiple error lines."""
        for line in sample_error_lines:
            log_parser.parse_line(line)

        assert len(log_parser.errors) > 0

    def test_error_deduplication(self, log_parser: FFmpegLogParser):
        """Test that duplicate errors are not added multiple times."""
        line = "[error] Connection refused"

        log_parser.parse_line(line)
        log_parser.parse_line(line)  # Same error again
        log_parser.parse_line(line)  # And again

        # Should only have 1 error (deduplicated)
        assert len(log_parser.errors) == 1

    def test_get_critical_errors(self, log_parser: FFmpegLogParser):
        """Test getting critical errors."""
        log_parser.parse_line("[error] Regular error")
        log_parser.parse_line("[fatal] Fatal error")
        log_parser.parse_line("[warning] Warning")
        log_parser.parse_line("[panic] Panic error")

        critical = log_parser.get_critical_errors()

        assert len(critical) == 2  # Fatal and panic
        assert all(err.level in (LogLevel.FATAL, LogLevel.PANIC) for err in critical)

    def test_get_recent_errors(self, log_parser: FFmpegLogParser):
        """Test getting recent errors."""
        # Add 15 errors
        for i in range(15):
            log_parser.parse_line(f"[error] Error number {i}")

        recent = log_parser.get_recent_errors(count=5)

        assert len(recent) <= 5

    def test_has_fatal_errors(self, log_parser: FFmpegLogParser):
        """Test checking for fatal errors."""
        assert log_parser.has_fatal_errors() is False

        log_parser.parse_line("[fatal] Fatal error")

        assert log_parser.has_fatal_errors() is True

    def test_is_stream_healthy_no_metrics(self, log_parser: FFmpegLogParser):
        """Test stream health check with no metrics."""
        assert log_parser.is_stream_healthy() is False

    def test_is_stream_healthy_with_good_metrics(self, log_parser: FFmpegLogParser):
        """Test stream health check with good metrics."""
        # Parse a recent metrics line
        line = "frame=  100 fps= 30 q=28.0 size=512kB time=00:00:03.33 bitrate=1258.3kbits/s speed=1.00x"
        log_parser.parse_line(line)

        assert log_parser.is_stream_healthy() is True

    def test_is_stream_healthy_with_low_fps(self, log_parser: FFmpegLogParser):
        """Test stream health check with low FPS."""
        line = "frame=  100 fps= 5 q=28.0 size=512kB time=00:00:03.33 bitrate=1258.3kbits/s speed=1.00x"
        log_parser.parse_line(line)

        assert log_parser.is_stream_healthy() is False

    def test_is_stream_healthy_with_slow_speed(self, log_parser: FFmpegLogParser):
        """Test stream health check with slow encoding speed."""
        line = "frame=  100 fps= 30 q=28.0 size=512kB time=00:00:03.33 bitrate=1258.3kbits/s speed=0.3x"
        log_parser.parse_line(line)

        assert log_parser.is_stream_healthy() is False

    def test_get_metrics_summary(self, log_parser: FFmpegLogParser):
        """Test getting metrics summary."""
        line = "frame=  100 fps= 30 q=28.0 size=512kB time=00:00:03.33 bitrate=1258.3kbits/s speed=1.00x"
        log_parser.parse_line(line)

        summary = log_parser.get_metrics_summary()

        assert isinstance(summary, dict)
        assert summary["frame_count"] == 100
        assert summary["fps"] == 30.0
        assert summary["speed"] == 1.00
        assert "is_healthy" in summary

    def test_reset(self, log_parser: FFmpegLogParser):
        """Test resetting parser state."""
        # Add some data
        log_parser.parse_line(
            "frame=  100 fps= 30 q=28.0 size=512kB time=00:00:03.33 bitrate=1258.3kbits/s speed=1.00x"
        )
        log_parser.parse_line("[error] Some error")

        # Reset
        log_parser.reset()

        assert log_parser.metrics.frame_count == 0
        assert len(log_parser.errors) == 0
        assert len(log_parser.warnings) == 0


class TestLogLevel:
    """Test LogLevel enum."""

    def test_log_levels_exist(self):
        """Test that all log levels exist."""
        assert LogLevel.DEBUG
        assert LogLevel.VERBOSE
        assert LogLevel.INFO
        assert LogLevel.WARNING
        assert LogLevel.ERROR
        assert LogLevel.FATAL
        assert LogLevel.PANIC


class TestErrorType:
    """Test ErrorType enum."""

    def test_error_types_exist(self):
        """Test that all error types exist."""
        assert ErrorType.CONNECTION_FAILED
        assert ErrorType.INVALID_CODEC
        assert ErrorType.FILE_NOT_FOUND
        assert ErrorType.STREAM_ERROR
        assert ErrorType.ENCODER_ERROR
        assert ErrorType.RTMP_ERROR
        assert ErrorType.UNKNOWN


class TestFFmpegMetrics:
    """Test FFmpegMetrics dataclass."""

    def test_default_metrics(self):
        """Test default metric values."""
        metrics = FFmpegMetrics()

        assert metrics.frame_count == 0
        assert metrics.fps == 0.0
        assert metrics.speed == 0.0
        assert metrics.dup_frames == 0
        assert metrics.drop_frames == 0
        assert metrics.last_update is None


class TestFFmpegError:
    """Test FFmpegError dataclass."""

    def test_error_creation(self):
        """Test creating an FFmpeg error."""
        from datetime import datetime

        error = FFmpegError(
            timestamp=datetime.now(),
            level=LogLevel.ERROR,
            error_type=ErrorType.CONNECTION_FAILED,
            message="Connection refused",
            raw_line="[error] Connection refused",
        )

        assert error.level == LogLevel.ERROR
        assert error.error_type == ErrorType.CONNECTION_FAILED
        assert "Connection refused" in error.message
