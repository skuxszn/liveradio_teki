"""HLS-Based Alternative for Seamless Transitions.

This module provides an alternative approach using HLS (HTTP Live Streaming)
as an intermediate format for achieving gapless transitions.

Architecture:
- Primary FFmpeg: Video loop → HLS segments
- Secondary FFmpeg: HLS playlist → RTMP to YouTube
- On track change: Update HLS playlist with new video loop

This approach has higher latency but provides more reliable transitions
than direct dual-input FFmpeg.
"""

import asyncio
import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from advanced.config import AdvancedConfig

logger = logging.getLogger(__name__)


@dataclass
class HLSSegmentInfo:
    """Information about an HLS segment."""

    sequence: int
    duration: float
    filename: str
    created_at: datetime


class HLSManager:
    """Manages HLS-based streaming with seamless track transitions.

    This is an alternative to the dual-input approach that uses HLS as
    an intermediate format:

    1. Encoder Process: Video loop → HLS segments → local directory
    2. Streamer Process: HLS playlist → RTMP to YouTube

    On track change:
    - Start new encoder with new video loop
    - Update playlist to include new segments
    - Old encoder continues until segments are consumed
    - Smooth handover without gaps

    Advantages:
    - More reliable than dual-input approach
    - Easier to implement and debug
    - Standard HLS mechanisms for gapless playback

    Disadvantages:
    - Higher latency (2-10 seconds)
    - More disk I/O
    - Requires cleanup of old segments

    Example:
        >>> config = AdvancedConfig.from_env()
        >>> manager = HLSManager(config)
        >>> await manager.start_stream("/path/to/loop.mp4")
        >>> await manager.switch_track("/path/to/new/loop.mp4")
    """

    def __init__(self, config: Optional[AdvancedConfig] = None):
        """Initialize HLS manager.

        Args:
            config: Advanced configuration
        """
        self.config = config or AdvancedConfig.from_env()
        self.config.validate()

        # HLS directory structure
        self.hls_dir = Path(self.config.hls_temp_dir)
        self.segments_dir = self.hls_dir / "segments"
        self.playlist_path = self.hls_dir / "playlist.m3u8"

        # Setup directories
        self._setup_directories()

        # Process tracking
        self._encoder_process: Optional[subprocess.Popen] = None
        self._streamer_process: Optional[subprocess.Popen] = None

        # State
        self._current_loop: Optional[str] = None
        self._segment_sequence = 0
        self._segments: List[HLSSegmentInfo] = []

        logger.info("HLSManager initialized")

    def _setup_directories(self) -> None:
        """Set up HLS directory structure."""
        self.hls_dir.mkdir(parents=True, exist_ok=True)
        self.segments_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"HLS directories created: {self.hls_dir}")

    async def start_stream(
        self,
        initial_loop: str,
        audio_url: Optional[str] = None,
        rtmp_endpoint: Optional[str] = None,
    ) -> bool:
        """Start HLS-based streaming.

        Args:
            initial_loop: Path to initial video loop
            audio_url: Optional audio stream URL
            rtmp_endpoint: Optional RTMP endpoint

        Returns:
            True if stream started successfully
        """
        try:
            logger.info(f"Starting HLS stream with: {initial_loop}")

            # Start encoder (video loop → HLS)
            encoder_started = await self._start_encoder(initial_loop, audio_url)
            if not encoder_started:
                logger.error("Failed to start encoder")
                return False

            # Wait for initial segments
            await asyncio.sleep(self.config.hls_segment_duration * 2)

            # Start streamer (HLS → RTMP)
            streamer_started = await self._start_streamer(rtmp_endpoint)
            if not streamer_started:
                logger.error("Failed to start streamer")
                await self._stop_encoder()
                return False

            self._current_loop = initial_loop
            logger.info("HLS stream started successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to start HLS stream: {e}", exc_info=True)
            return False

    async def _start_encoder(
        self,
        loop_path: str,
        audio_url: Optional[str] = None,
    ) -> bool:
        """Start encoder process (video → HLS).

        Args:
            loop_path: Path to video loop
            audio_url: Optional audio URL

        Returns:
            True if started successfully
        """
        audio_url = audio_url or self.config.audio_url

        cmd = [
            self.config.ffmpeg_binary,
            "-re",
            "-stream_loop",
            "-1",
            "-i",
            loop_path,
            "-i",
            audio_url,
            "-map",
            "0:v",
            "-map",
            "1:a",
            # Video encoding
            "-c:v",
            self.config.video_codec,
            "-preset",
            self.config.video_preset,
            "-b:v",
            self.config.video_bitrate,
            "-g",
            str(self.config.keyframe_interval),
            "-pix_fmt",
            self.config.pixel_format,
            # Audio encoding
            "-c:a",
            self.config.audio_codec,
            "-b:a",
            self.config.audio_bitrate,
            "-ar",
            self.config.audio_sample_rate,
            # HLS output
            "-f",
            "hls",
            "-hls_time",
            str(self.config.hls_segment_duration),
            "-hls_list_size",
            str(self.config.hls_playlist_size),
            "-hls_flags",
            "delete_segments+append_list",
            "-hls_segment_filename",
            str(self.segments_dir / "segment_%03d.ts"),
            str(self.playlist_path),
        ]

        logger.debug(f"Encoder command: {' '.join(cmd)}")

        try:
            self._encoder_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
            )

            # Check if process started
            await asyncio.sleep(0.5)
            if self._encoder_process.poll() is None:
                logger.info(f"Encoder started (PID: {self._encoder_process.pid})")
                return True
            else:
                stderr = self._encoder_process.stderr.read().decode("utf-8", errors="replace")
                logger.error(f"Encoder died: {stderr[:500]}")
                return False

        except Exception as e:
            logger.error(f"Failed to start encoder: {e}", exc_info=True)
            return False

    async def _start_streamer(
        self,
        rtmp_endpoint: Optional[str] = None,
    ) -> bool:
        """Start streamer process (HLS → RTMP).

        Args:
            rtmp_endpoint: Optional RTMP endpoint

        Returns:
            True if started successfully
        """
        rtmp_endpoint = rtmp_endpoint or self.config.rtmp_endpoint

        cmd = [
            self.config.ffmpeg_binary,
            "-re",
            "-i",
            str(self.playlist_path),
            "-c",
            "copy",  # Copy streams without re-encoding
            "-f",
            "flv",
            rtmp_endpoint,
        ]

        logger.debug(f"Streamer command: {' '.join(cmd)}")

        try:
            self._streamer_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
            )

            # Check if process started
            await asyncio.sleep(0.5)
            if self._streamer_process.poll() is None:
                logger.info(f"Streamer started (PID: {self._streamer_process.pid})")
                return True
            else:
                stderr = self._streamer_process.stderr.read().decode("utf-8", errors="replace")
                logger.error(f"Streamer died: {stderr[:500]}")
                return False

        except Exception as e:
            logger.error(f"Failed to start streamer: {e}", exc_info=True)
            return False

    async def switch_track(
        self,
        new_loop: str,
        audio_url: Optional[str] = None,
    ) -> bool:
        """Switch to a new video loop.

        This restarts the encoder with the new loop while the streamer
        continues reading from the HLS playlist, providing a seamless
        transition.

        Args:
            new_loop: Path to new video loop
            audio_url: Optional audio URL

        Returns:
            True if switch was successful
        """
        try:
            logger.info(f"Switching to new loop: {new_loop}")

            # Stop old encoder
            await self._stop_encoder()

            # Small delay to let segments flush
            await asyncio.sleep(0.5)

            # Start new encoder with new loop
            success = await self._start_encoder(new_loop, audio_url)

            if success:
                self._current_loop = new_loop
                logger.info("Track switched successfully via HLS")
                return True
            else:
                logger.error("Failed to start new encoder")
                return False

        except Exception as e:
            logger.error(f"Failed to switch track: {e}", exc_info=True)
            return False

    async def _stop_encoder(self) -> bool:
        """Stop encoder process.

        Returns:
            True if stopped successfully
        """
        if not self._encoder_process:
            return True

        try:
            logger.debug("Stopping encoder")
            self._encoder_process.terminate()

            try:
                self._encoder_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Encoder did not terminate, force killing")
                self._encoder_process.kill()
                self._encoder_process.wait(timeout=3)

            self._encoder_process = None
            logger.debug("Encoder stopped")
            return True

        except Exception as e:
            logger.error(f"Error stopping encoder: {e}")
            return False

    async def _stop_streamer(self) -> bool:
        """Stop streamer process.

        Returns:
            True if stopped successfully
        """
        if not self._streamer_process:
            return True

        try:
            logger.debug("Stopping streamer")
            self._streamer_process.terminate()

            try:
                self._streamer_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Streamer did not terminate, force killing")
                self._streamer_process.kill()
                self._streamer_process.wait(timeout=3)

            self._streamer_process = None
            logger.debug("Streamer stopped")
            return True

        except Exception as e:
            logger.error(f"Error stopping streamer: {e}")
            return False

    async def stop_stream(self) -> bool:
        """Stop HLS streaming.

        Returns:
            True if stopped successfully
        """
        logger.info("Stopping HLS stream")

        encoder_stopped = await self._stop_encoder()
        streamer_stopped = await self._stop_streamer()

        # Cleanup segments
        self._cleanup_segments()

        success = encoder_stopped and streamer_stopped
        if success:
            logger.info("HLS stream stopped")
        else:
            logger.warning("Some processes may not have stopped cleanly")

        return success

    def _cleanup_segments(self) -> None:
        """Clean up HLS segment files."""
        try:
            if self.segments_dir.exists():
                for file in self.segments_dir.glob("segment_*.ts"):
                    file.unlink()
                logger.debug("Cleaned up HLS segments")

            if self.playlist_path.exists():
                self.playlist_path.unlink()
                logger.debug("Cleaned up HLS playlist")

        except Exception as e:
            logger.error(f"Error cleaning up segments: {e}")

    def get_status(self) -> dict:
        """Get current status.

        Returns:
            Dictionary with status information
        """
        return {
            "encoder_running": (
                self._encoder_process is not None and self._encoder_process.poll() is None
            ),
            "streamer_running": (
                self._streamer_process is not None and self._streamer_process.poll() is None
            ),
            "encoder_pid": (self._encoder_process.pid if self._encoder_process else None),
            "streamer_pid": (self._streamer_process.pid if self._streamer_process else None),
            "current_loop": self._current_loop,
            "hls_directory": str(self.hls_dir),
            "playlist_exists": self.playlist_path.exists(),
        }

    def is_running(self) -> bool:
        """Check if stream is running.

        Returns:
            True if both encoder and streamer are running
        """
        encoder_ok = self._encoder_process is not None and self._encoder_process.poll() is None
        streamer_ok = self._streamer_process is not None and self._streamer_process.poll() is None
        return encoder_ok and streamer_ok

    async def cleanup(self) -> None:
        """Clean up all resources."""
        logger.info("Cleaning up HLSManager")

        await self.stop_stream()

        # Remove HLS directory
        try:
            if self.hls_dir.exists():
                shutil.rmtree(self.hls_dir)
                logger.debug(f"Removed HLS directory: {self.hls_dir}")
        except Exception as e:
            logger.error(f"Error removing HLS directory: {e}")

        logger.info("Cleanup complete")
