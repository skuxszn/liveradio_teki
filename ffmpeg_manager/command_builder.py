"""
FFmpeg command builder.

Constructs FFmpeg commands with proper encoding settings, fade transitions,
and RTMP output configuration.
"""

import logging
from typing import List, Optional

from ffmpeg_manager.config import EncodingConfig, FFmpegConfig

logger = logging.getLogger(__name__)


class FFmpegCommandBuilder:
    """
    Builds FFmpeg commands for streaming video loops with live audio.

    Supports fade transitions, multiple encoding presets, and both CPU/GPU encoding.
    """

    def __init__(self, config: FFmpegConfig):
        """
        Initialize command builder.

        Args:
            config: FFmpeg configuration
        """
        self.config = config
        self.encoding_config = config.get_encoding_config()

    def build_command(
        self,
        loop_path: str,
        audio_url: Optional[str] = None,
        rtmp_endpoint: Optional[str] = None,
        fade_in: bool = True,
    ) -> List[str]:
        """
        Build complete FFmpeg command for streaming.

        Args:
            loop_path: Absolute path to video loop file
            audio_url: HTTP URL of audio stream (defaults to config)
            rtmp_endpoint: RTMP endpoint for output (defaults to config)
            fade_in: Whether to apply fade-in transition

        Returns:
            List of command arguments for subprocess

        Raises:
            ValueError: If loop_path is empty or invalid
        """
        if not loop_path or not loop_path.strip():
            raise ValueError("loop_path cannot be empty")

        audio_url = audio_url or self.config.audio_url
        rtmp_endpoint = rtmp_endpoint or self.config.rtmp_endpoint

        cmd = [self.config.ffmpeg_binary]

        # Global options
        cmd.extend(self._build_global_options())

        # Video input (looping)
        cmd.extend(self._build_video_input(loop_path))

        # Audio input (live stream)
        cmd.extend(self._build_audio_input(audio_url))

        # Stream mapping
        cmd.extend(["-map", "0:v", "-map", "1:a"])

        # Video encoding
        cmd.extend(self._build_video_encoding(fade_in))

        # Audio encoding
        cmd.extend(self._build_audio_encoding(fade_in))

        # Output options
        cmd.extend(self._build_output_options(rtmp_endpoint))

        logger.debug(f"Built FFmpeg command: {' '.join(cmd)}")
        return cmd

    def _build_global_options(self) -> List[str]:
        """Build global FFmpeg options."""
        return [
            "-re",  # Read input at native frame rate (essential for live streaming)
            "-loglevel",
            self.config.log_level,
            "-hide_banner",  # Hide FFmpeg banner in output
            "-nostats",  # Don't show encoding statistics
        ]

    def _build_video_input(self, loop_path: str) -> List[str]:
        """Build video input options."""
        return [
            "-stream_loop",
            "-1",  # Loop indefinitely
            "-thread_queue_size",
            str(self.config.thread_queue_size),
            "-i",
            loop_path,
        ]

    def _build_audio_input(self, audio_url: str) -> List[str]:
        """Build audio input options."""
        return [
            "-thread_queue_size",
            str(self.config.thread_queue_size),
            "-i",
            audio_url,
        ]

    def _build_video_encoding(self, fade_in: bool) -> List[str]:
        """Build video encoding options with optional fade."""
        enc = self.encoding_config
        options = []

        # Video filters
        filters = []

        # Fade-in filter (applied at start of stream)
        if fade_in and self.config.fade_in_duration > 0:
            fade_frames = int(self.config.fade_in_duration * enc.framerate)
            filters.append(f"fade=t=in:st=0:d={self.config.fade_in_duration}:n={fade_frames}")

        # Scale to target resolution
        filters.append(f"scale={enc.resolution}")

        # Pixel format conversion
        filters.append(f"format={enc.pixel_format}")

        # Set frame rate
        filters.append(f"fps={enc.framerate}")

        # Combine filters
        if filters:
            options.extend(["-vf", ",".join(filters)])

        # Video codec
        options.extend(["-c:v", enc.video_codec])

        # Codec-specific options
        if enc.use_nvenc:
            # NVENC options
            options.extend([
                "-preset", enc.video_preset,
                "-rc", "vbr",  # Variable bitrate
                "-cq", "23",  # Constant quality (lower = better, 0-51)
                "-b:v", enc.video_bitrate,
                "-maxrate", enc.video_bitrate,
                "-bufsize", f"{int(enc.video_bitrate.rstrip('k')) * 2}k",
                "-profile:v", "high",
                "-level", "4.2",
            ])
        else:
            # x264 options
            options.extend([
                "-preset", enc.video_preset,
                "-tune", "zerolatency",  # Optimize for low latency
                "-b:v", enc.video_bitrate,
                "-maxrate", enc.video_bitrate,
                "-bufsize", f"{int(enc.video_bitrate.rstrip('k')) * 2}k",
                "-profile:v", "high",
                "-level", "4.2",
            ])

        # Keyframe interval (GOP size)
        options.extend([
            "-g", str(enc.keyframe_interval),
            "-keyint_min", str(enc.keyframe_interval),
            "-sc_threshold", "0",  # Disable scene change detection
        ])

        # Pixel format
        options.extend(["-pix_fmt", enc.pixel_format])

        return options

    def _build_audio_encoding(self, fade_in: bool) -> List[str]:
        """Build audio encoding options with optional fade."""
        enc = self.encoding_config
        options = []

        # Audio filters
        filters = []

        # Fade-in filter
        if fade_in and self.config.fade_in_duration > 0:
            filters.append(f"afade=t=in:ss=0:d={self.config.fade_in_duration}")

        # Apply filters if any
        if filters:
            options.extend(["-af", ",".join(filters)])

        # Audio codec
        options.extend(["-c:a", enc.audio_codec])

        # Audio bitrate
        options.extend(["-b:a", enc.audio_bitrate])

        # Sample rate
        options.extend(["-ar", enc.audio_sample_rate])

        # Audio channels (stereo)
        options.extend(["-ac", "2"])

        return options

    def _build_output_options(self, rtmp_endpoint: str) -> List[str]:
        """Build output format options."""
        return [
            "-f", "flv",  # Flash Video format for RTMP
            rtmp_endpoint,
        ]

    def get_command_string(
        self,
        loop_path: str,
        audio_url: Optional[str] = None,
        rtmp_endpoint: Optional[str] = None,
        fade_in: bool = True,
    ) -> str:
        """
        Get FFmpeg command as a single string (useful for logging).

        Args:
            loop_path: Absolute path to video loop file
            audio_url: HTTP URL of audio stream
            rtmp_endpoint: RTMP endpoint for output
            fade_in: Whether to apply fade-in transition

        Returns:
            Space-separated command string
        """
        cmd = self.build_command(loop_path, audio_url, rtmp_endpoint, fade_in)
        return " ".join(cmd)

    def validate_encoding_compatibility(self) -> bool:
        """
        Validate that the system supports the selected encoding preset.

        For NVENC presets, this would check if NVIDIA GPU is available.
        For now, returns True (validation can be added later).

        Returns:
            True if encoding preset is compatible with the system
        """
        # TODO: Implement GPU detection for NVENC validation
        if self.encoding_config.use_nvenc:
            logger.warning(
                "NVENC encoding selected but GPU validation not implemented. "
                "FFmpeg will fail if NVIDIA GPU is not available."
            )
        return True


def create_command_builder(config: Optional[FFmpegConfig] = None) -> FFmpegCommandBuilder:
    """
    Factory function to create a command builder.

    Args:
        config: Optional FFmpeg configuration (creates default if not provided)

    Returns:
        FFmpegCommandBuilder instance
    """
    if config is None:
        from ffmpeg_manager.config import get_config
        config = get_config()

    return FFmpegCommandBuilder(config)



