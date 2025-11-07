"""
FFmpeg log parser.

Parses FFmpeg stderr output in real-time to detect errors, warnings,
performance issues, and extract useful metrics.
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class LogLevel(str, Enum):
    """FFmpeg log levels."""

    DEBUG = "debug"
    VERBOSE = "verbose"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"
    PANIC = "panic"


class ErrorType(str, Enum):
    """Types of FFmpeg errors."""

    CONNECTION_FAILED = "connection_failed"
    INVALID_CODEC = "invalid_codec"
    FILE_NOT_FOUND = "file_not_found"
    STREAM_ERROR = "stream_error"
    ENCODER_ERROR = "encoder_error"
    DECODER_ERROR = "decoder_error"
    MEMORY_ERROR = "memory_error"
    IO_ERROR = "io_error"
    RTMP_ERROR = "rtmp_error"
    AUDIO_ERROR = "audio_error"
    VIDEO_ERROR = "video_error"
    UNKNOWN = "unknown"


@dataclass
class FFmpegMetrics:
    """Metrics extracted from FFmpeg output."""

    frame_count: int = 0
    fps: float = 0.0
    bitrate: str = "0kbits/s"
    speed: float = 0.0
    time: str = "00:00:00.00"
    dup_frames: int = 0
    drop_frames: int = 0
    last_update: Optional[datetime] = None


@dataclass
class FFmpegError:
    """Represents an FFmpeg error or warning."""

    timestamp: datetime
    level: LogLevel
    error_type: ErrorType
    message: str
    raw_line: str


class FFmpegLogParser:
    """
    Parses FFmpeg stderr output to extract metrics and detect errors.

    Uses regex patterns to identify different types of errors and extract
    real-time encoding statistics.
    """

    # Regex patterns for error detection
    ERROR_PATTERNS = {
        ErrorType.CONNECTION_FAILED: [
            r"Connection (?:refused|timed out|reset)",
            r"Failed to connect",
            r"Unable to connect",
            r"Could not (?:open|connect)",
        ],
        ErrorType.FILE_NOT_FOUND: [
            r"No such file or directory",
            r"does not exist",
            r"cannot find the path",
        ],
        ErrorType.INVALID_CODEC: [
            r"Unknown (?:encoder|decoder|codec)",
            r"Unsupported codec",
            r"Invalid codec",
        ],
        ErrorType.RTMP_ERROR: [
            r"RTMP.*error",
            r"Failed to update RTMP",
            r"RTMP.*connection.*closed",
        ],
        ErrorType.ENCODER_ERROR: [
            r"Encoding failed",
            r"Encoder.*error",
            r"Error (?:encoding|while encoding)",
        ],
        ErrorType.DECODER_ERROR: [
            r"Decoding failed",
            r"Decoder.*error",
            r"Error (?:decoding|while decoding)",
        ],
        ErrorType.MEMORY_ERROR: [
            r"Cannot allocate memory",
            r"Out of memory",
            r"Memory allocation failed",
        ],
        ErrorType.IO_ERROR: [
            r"I/O error",
            r"Input/output error",
            r"Read error",
            r"Write error",
        ],
        ErrorType.STREAM_ERROR: [
            r"Invalid stream",
            r"Stream.*error",
            r"Error in stream",
        ],
        ErrorType.AUDIO_ERROR: [
            r"Audio.*error",
            r"Invalid audio",
            r"No audio",
        ],
        ErrorType.VIDEO_ERROR: [
            r"Video.*error",
            r"Invalid video",
            r"No video",
        ],
    }

    # Regex for extracting metrics from progress lines
    METRICS_PATTERN = re.compile(
        r"frame=\s*(\d+)\s+"
        r"fps=\s*([\d.]+)\s+"
        r".*?size=.*?"
        r"time=\s*([\d:.]+)\s+"
        r"bitrate=\s*([\d.]+\w+/s)\s+"
        r"(?:dup=\s*(\d+)\s+)?"
        r"(?:drop=\s*(\d+)\s+)?"
        r"speed=\s*([\d.]+)x"
    )

    # Compiled error patterns
    COMPILED_PATTERNS: Dict[ErrorType, List[re.Pattern]] = {}

    @classmethod
    def _compile_patterns(cls) -> None:
        """Compile regex patterns for error detection."""
        if not cls.COMPILED_PATTERNS:
            for error_type, patterns in cls.ERROR_PATTERNS.items():
                cls.COMPILED_PATTERNS[error_type] = [
                    re.compile(pattern, re.IGNORECASE) for pattern in patterns
                ]

    def __init__(self):
        """Initialize log parser."""
        self._compile_patterns()
        self.metrics = FFmpegMetrics()
        self.errors: List[FFmpegError] = []
        self.warnings: List[FFmpegError] = []
        self._seen_errors: Set[str] = set()  # Deduplicate errors

    def parse_line(self, line: str) -> Optional[FFmpegError]:
        """
        Parse a single line of FFmpeg output.

        Args:
            line: Line of FFmpeg stderr output

        Returns:
            FFmpegError if an error/warning is detected, None otherwise
        """
        line = line.strip()
        if not line:
            return None

        # Update metrics if this is a progress line
        self._update_metrics(line)

        # Check for errors and warnings
        error = self._detect_error(line)
        if error:
            # Deduplicate similar errors
            error_key = f"{error.error_type}:{error.message[:50]}"
            if error_key not in self._seen_errors:
                self._seen_errors.add(error_key)
                if error.level in (LogLevel.ERROR, LogLevel.FATAL, LogLevel.PANIC):
                    self.errors.append(error)
                else:
                    self.warnings.append(error)
                return error

        return None

    def _update_metrics(self, line: str) -> None:
        """Extract metrics from FFmpeg progress output."""
        match = self.METRICS_PATTERN.search(line)
        if match:
            try:
                self.metrics.frame_count = int(match.group(1))
                self.metrics.fps = float(match.group(2))
                self.metrics.time = match.group(3)
                self.metrics.bitrate = match.group(4)

                # Optional dup/drop frames
                if match.group(5):
                    self.metrics.dup_frames = int(match.group(5))
                if match.group(6):
                    self.metrics.drop_frames = int(match.group(6))

                self.metrics.speed = float(match.group(7))
                self.metrics.last_update = datetime.now()

                logger.debug(
                    f"Metrics: frame={self.metrics.frame_count} "
                    f"fps={self.metrics.fps} speed={self.metrics.speed}x"
                )
            except (ValueError, IndexError) as e:
                logger.debug(f"Failed to parse metrics from line: {e}")

    def _detect_error(self, line: str) -> Optional[FFmpegError]:
        """Detect errors and warnings in a log line."""
        # Determine log level
        level = self._get_log_level(line)

        # Only process warning/error/fatal level messages
        if level not in (LogLevel.WARNING, LogLevel.ERROR, LogLevel.FATAL, LogLevel.PANIC):
            return None

        # Match against error patterns
        for error_type, patterns in self.COMPILED_PATTERNS.items():
            for pattern in patterns:
                if pattern.search(line):
                    message = self._extract_error_message(line)
                    return FFmpegError(
                        timestamp=datetime.now(),
                        level=level,
                        error_type=error_type,
                        message=message,
                        raw_line=line,
                    )

        # If we detected a warning/error level but didn't match a pattern
        if level in (LogLevel.ERROR, LogLevel.FATAL, LogLevel.PANIC):
            return FFmpegError(
                timestamp=datetime.now(),
                level=level,
                error_type=ErrorType.UNKNOWN,
                message=self._extract_error_message(line),
                raw_line=line,
            )

        return None

    def _get_log_level(self, line: str) -> LogLevel:
        """Extract log level from a line."""
        line_lower = line.lower()

        if "[fatal]" in line_lower or "fatal error" in line_lower:
            return LogLevel.FATAL
        elif "[panic]" in line_lower:
            return LogLevel.PANIC
        elif "[error]" in line_lower or "error" in line_lower:
            return LogLevel.ERROR
        elif "[warning]" in line_lower or "warning" in line_lower:
            return LogLevel.WARNING
        elif "[verbose]" in line_lower:
            return LogLevel.VERBOSE
        elif "[debug]" in line_lower:
            return LogLevel.DEBUG
        else:
            return LogLevel.INFO

    def _extract_error_message(self, line: str) -> str:
        """Extract the error message from a log line."""
        # Remove FFmpeg prefix patterns
        message = re.sub(r"^\[[\w@]+\s*\]\s*", "", line)
        message = re.sub(r"^ffmpeg\s*:\s*", "", message, flags=re.IGNORECASE)

        # Truncate if too long
        if len(message) > 200:
            message = message[:197] + "..."

        return message.strip()

    def get_critical_errors(self) -> List[FFmpegError]:
        """
        Get list of critical errors (FATAL, PANIC).

        Returns:
            List of critical errors
        """
        return [err for err in self.errors if err.level in (LogLevel.FATAL, LogLevel.PANIC)]

    def get_recent_errors(self, count: int = 10) -> List[FFmpegError]:
        """
        Get most recent errors.

        Args:
            count: Number of errors to return

        Returns:
            List of recent errors
        """
        return self.errors[-count:]

    def has_fatal_errors(self) -> bool:
        """
        Check if any fatal errors have been detected.

        Returns:
            True if fatal errors exist
        """
        return len(self.get_critical_errors()) > 0

    def is_stream_healthy(self) -> bool:
        """
        Check if stream appears healthy based on metrics.

        Returns:
            True if stream metrics indicate healthy operation
        """
        if not self.metrics.last_update:
            return False

        # Check if metrics are recent (updated within last 5 seconds)
        elapsed = (datetime.now() - self.metrics.last_update).total_seconds()
        if elapsed > 5:
            logger.warning(f"Metrics stale: {elapsed:.1f}s since last update")
            return False

        # Check if FPS is reasonable (should be close to target)
        if self.metrics.fps < 10:
            logger.warning(f"Low FPS detected: {self.metrics.fps}")
            return False

        # Check encoding speed
        if self.metrics.speed < 0.5:
            logger.warning(f"Slow encoding speed: {self.metrics.speed}x")
            return False

        # Check for excessive dropped frames
        if self.metrics.drop_frames > 100:
            logger.warning(f"High drop frames: {self.metrics.drop_frames}")
            return False

        return True

    def get_metrics_summary(self) -> Dict:
        """
        Get summary of current metrics.

        Returns:
            Dictionary with metric values
        """
        return {
            "frame_count": self.metrics.frame_count,
            "fps": self.metrics.fps,
            "bitrate": self.metrics.bitrate,
            "speed": self.metrics.speed,
            "time": self.metrics.time,
            "dup_frames": self.metrics.dup_frames,
            "drop_frames": self.metrics.drop_frames,
            "last_update": (
                self.metrics.last_update.isoformat() if self.metrics.last_update else None
            ),
            "total_errors": len(self.errors),
            "total_warnings": len(self.warnings),
            "is_healthy": self.is_stream_healthy(),
        }

    def reset(self) -> None:
        """Reset parser state (for new FFmpeg process)."""
        self.metrics = FFmpegMetrics()
        self.errors = []
        self.warnings = []
        self._seen_errors = set()
        logger.debug("Log parser state reset")
