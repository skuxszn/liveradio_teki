"""
Video file validation using ffprobe.

This module provides functionality to validate MP4 loop files for format,
resolution, duration, and codec compliance.
"""

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from asset_manager.config import AssetConfig, get_config

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of video file validation."""

    valid: bool
    file_path: str
    errors: list[str]
    metadata: Optional[dict] = None

    def add_error(self, error: str) -> None:
        """Add an error to the validation result."""
        self.errors.append(error)
        self.valid = False


@dataclass
class VideoMetadata:
    """Video file metadata extracted from ffprobe."""

    duration: float
    width: int
    height: int
    video_codec: str
    audio_codec: Optional[str]
    bitrate: int
    fps: float
    format_name: str
    file_size: int

    def to_dict(self) -> dict:
        """Convert metadata to dictionary."""
        return {
            "duration": self.duration,
            "width": self.width,
            "height": self.height,
            "video_codec": self.video_codec,
            "audio_codec": self.audio_codec,
            "bitrate": self.bitrate,
            "fps": self.fps,
            "format_name": self.format_name,
            "file_size": self.file_size,
        }


class VideoValidator:
    """Validator for video loop files."""

    def __init__(self, config: Optional[AssetConfig] = None):
        """
        Initialize the video validator.

        Args:
            config: Asset configuration. If None, uses default config.
        """
        self.config = config or get_config()
        self.logger = logging.getLogger(__name__)

    def validate_loop(self, file_path: str) -> ValidationResult:
        """
        Validate a video loop file.

        Checks:
        - File exists and is readable
        - Format is MP4 container
        - Video codec is H.264
        - Resolution matches target
        - Duration is at least minimum required
        - Audio codec is allowed (AAC or none)

        Args:
            file_path: Path to the video file

        Returns:
            ValidationResult with validation status and any errors
        """
        result = ValidationResult(valid=True, file_path=file_path, errors=[])

        # Check file exists
        path = Path(file_path)
        if not path.exists():
            result.add_error(f"File does not exist: {file_path}")
            return result

        if not path.is_file():
            result.add_error(f"Path is not a file: {file_path}")
            return result

        # Check file is readable
        try:
            with open(file_path, "rb"):
                pass
        except PermissionError:
            result.add_error(f"File is not readable: {file_path}")
            return result
        except Exception as e:
            result.add_error(f"Error accessing file: {e}")
            return result

        # Extract metadata using ffprobe
        try:
            metadata = self.get_loop_metadata(file_path)
            result.metadata = metadata.to_dict()
        except Exception as e:
            result.add_error(f"Failed to extract metadata: {e}")
            return result

        # Validate format
        if "mp4" not in metadata.format_name.lower():
            result.add_error(f"Invalid format: {metadata.format_name} (expected MP4 container)")

        # Validate video codec
        expected_codec = self.config.required_video_codec
        if metadata.video_codec.lower() != expected_codec.lower():
            result.add_error(
                f"Invalid video codec: {metadata.video_codec} (expected {expected_codec})"
            )

        # Validate resolution
        target_width = self.config.get_target_width()
        target_height = self.config.get_target_height()
        if metadata.width != target_width or metadata.height != target_height:
            result.add_error(
                f"Invalid resolution: {metadata.width}x{metadata.height} "
                f"(expected {target_width}x{target_height})"
            )

        # Validate duration
        if metadata.duration < self.config.min_duration_seconds:
            result.add_error(
                f"Duration too short: {metadata.duration}s "
                f"(minimum {self.config.min_duration_seconds}s)"
            )

        # Validate audio codec (if present)
        allowed_codecs = self.config.get_allowed_audio_codecs_list()
        if metadata.audio_codec:
            if metadata.audio_codec.lower() not in [c.lower() for c in allowed_codecs]:
                result.add_error(
                    f"Invalid audio codec: {metadata.audio_codec} "
                    f"(allowed: {', '.join(allowed_codecs)})"
                )

        return result

    def get_loop_metadata(self, file_path: str) -> VideoMetadata:
        """
        Extract metadata from a video file using ffprobe.

        Args:
            file_path: Path to the video file

        Returns:
            VideoMetadata object with extracted information

        Raises:
            subprocess.CalledProcessError: If ffprobe fails
            KeyError: If expected metadata is missing
            ValueError: If metadata values are invalid
        """
        cmd = [
            self.config.ffprobe_path,
            "-v",
            "error",
            "-show_format",
            "-show_streams",
            "-of",
            "json",
            file_path,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.validation_timeout_seconds,
                check=True,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"ffprobe timeout after {self.config.validation_timeout_seconds}s")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"ffprobe failed: {e.stderr}")
        except FileNotFoundError:
            raise RuntimeError(
                f"ffprobe not found at: {self.config.ffprobe_path}. "
                "Please install ffmpeg or set FFPROBE_PATH environment variable."
            )

        try:
            probe_data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse ffprobe output: {e}")

        # Extract video stream info
        video_stream = None
        audio_stream = None

        for stream in probe_data.get("streams", []):
            if stream.get("codec_type") == "video" and video_stream is None:
                video_stream = stream
            elif stream.get("codec_type") == "audio" and audio_stream is None:
                audio_stream = stream

        if not video_stream:
            raise RuntimeError("No video stream found in file")

        # Extract format info
        format_info = probe_data.get("format", {})

        # Build metadata object
        try:
            metadata = VideoMetadata(
                duration=float(format_info.get("duration", 0)),
                width=int(video_stream.get("width", 0)),
                height=int(video_stream.get("height", 0)),
                video_codec=video_stream.get("codec_name", "unknown"),
                audio_codec=audio_stream.get("codec_name") if audio_stream else None,
                bitrate=int(format_info.get("bit_rate", 0)),
                fps=self._extract_fps(video_stream),
                format_name=format_info.get("format_name", "unknown"),
                file_size=int(format_info.get("size", 0)),
            )
        except (KeyError, ValueError) as e:
            raise RuntimeError(f"Failed to extract metadata: {e}")

        return metadata

    def _extract_fps(self, video_stream: dict) -> float:
        """
        Extract FPS from video stream data.

        Args:
            video_stream: Video stream dictionary from ffprobe

        Returns:
            FPS as float, or 0.0 if not available
        """
        fps_str = video_stream.get("r_frame_rate", "0/1")
        try:
            numerator, denominator = fps_str.split("/")
            fps = float(numerator) / float(denominator)
            return round(fps, 2)
        except (ValueError, ZeroDivisionError):
            return 0.0
