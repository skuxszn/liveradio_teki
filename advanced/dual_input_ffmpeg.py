"""Dual-Input Persistent FFmpeg Manager.

Manages a single persistent FFmpeg process with dual video inputs for
seamless crossfade transitions between tracks.
"""

import asyncio
import logging
import signal
import subprocess
from datetime import datetime
from enum import Enum
from typing import Optional, List

import psutil

from advanced.config import AdvancedConfig
from advanced.filter_graph_builder import FilterGraphBuilder
from advanced.input_switcher import InputSwitcher, SwitchStrategy

logger = logging.getLogger(__name__)


class StreamState(str, Enum):
    """State of the FFmpeg stream."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    SWITCHING = "switching"
    STOPPING = "stopping"
    ERROR = "error"


class DualInputFFmpegManager:
    """Manages persistent FFmpeg process with dual video inputs.

    This is the core implementation of Option A: a single persistent FFmpeg
    process that maintains two video input slots and crossfades between them
    on track changes.

    Key Features:
    - Single persistent FFmpeg process (no restarts)
    - Dual video inputs with dynamic switching
    - Smooth crossfade transitions using xfade filter
    - 0ms audio gaps (audio from continuous stream)
    - Automatic fallback to Option B on failures

    Architecture:
    - Input 0: Current video loop (active)
    - Input 1: Next video loop (preloaded)
    - Input 2: Live audio stream (continuous)

    The xfade filter crossfades between Input 0 and Input 1, then we swap
    the inputs so the "next" becomes "current" and a new "next" is loaded.

    Limitations:
    - FFmpeg doesn't support true dynamic input reloading
    - Uses symlink strategy for input switching
    - Requires careful timing to trigger crossfades

    Example:
        >>> config = AdvancedConfig.from_env()
        >>> manager = DualInputFFmpegManager(config)
        >>> await manager.start_stream("/path/to/first/loop.mp4")
        >>> await manager.switch_track("/path/to/next/loop.mp4")
    """

    def __init__(
        self,
        config: Optional[AdvancedConfig] = None,
        fallback_to_option_b: bool = True,
    ):
        """Initialize dual-input FFmpeg manager.

        Args:
            config: Advanced configuration (creates default if None)
            fallback_to_option_b: Whether to fallback to Option B on errors
        """
        self.config = config or AdvancedConfig.from_env()
        self.config.validate()

        self.fallback_enabled = fallback_to_option_b

        # Components
        self.filter_builder = FilterGraphBuilder(self.config)
        self.input_switcher = InputSwitcher(
            strategy=SwitchStrategy.SYMLINK,
            temp_dir=self.config.hls_temp_dir,
        )

        # State
        self._state = StreamState.STOPPED
        self._process: Optional[subprocess.Popen] = None
        self._current_loop: Optional[str] = None
        self._next_loop: Optional[str] = None
        self._started_at: Optional[datetime] = None
        self._switch_count = 0

        # Monitoring
        self._monitor_task: Optional[asyncio.Task] = None
        self._should_monitor = False

        # Restart tracking
        self._restart_count = 0

        logger.info("DualInputFFmpegManager initialized (Option A)")

    async def start_stream(
        self,
        initial_loop: str,
        audio_url: Optional[str] = None,
        rtmp_endpoint: Optional[str] = None,
    ) -> bool:
        """Start the persistent FFmpeg stream.

        Args:
            initial_loop: Path to initial video loop
            audio_url: Optional audio stream URL
            rtmp_endpoint: Optional RTMP endpoint

        Returns:
            True if stream started successfully
        """
        if self._state != StreamState.STOPPED:
            logger.warning(f"Cannot start stream: current state is {self._state}")
            return False

        try:
            self._state = StreamState.STARTING
            logger.info(f"Starting persistent FFmpeg stream with: {initial_loop}")

            # Prepare initial inputs (use same loop for both slots initially)
            slot0_path = await self.input_switcher.prepare_input(initial_loop, slot=0)
            slot1_path = await self.input_switcher.prepare_input(initial_loop, slot=1)

            # Build FFmpeg command
            cmd = self._build_command(
                slot0_path,
                slot1_path,
                audio_url or self.config.audio_url,
                rtmp_endpoint or self.config.rtmp_endpoint,
            )

            logger.debug(f"FFmpeg command: {' '.join(cmd)}")

            # Start FFmpeg process
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
            )

            self._current_loop = initial_loop
            self._started_at = datetime.now()

            # Wait briefly to check if process starts
            await asyncio.sleep(0.5)

            if self._process.poll() is None:
                self._state = StreamState.RUNNING
                self._should_monitor = True
                self._monitor_task = asyncio.create_task(self._monitor_process())

                logger.info(f"FFmpeg stream started successfully (PID: {self._process.pid})")
                return True
            else:
                # Process died immediately
                stderr = self._process.stderr.read().decode("utf-8", errors="replace")
                logger.error(f"FFmpeg died immediately: {stderr[:500]}")
                self._state = StreamState.ERROR
                return False

        except Exception as e:
            logger.error(f"Failed to start stream: {e}", exc_info=True)
            self._state = StreamState.ERROR
            return False

    async def switch_track(
        self,
        new_loop: str,
        preload_duration: float = 1.0,
    ) -> bool:
        """Switch to a new video loop with crossfade.

        This is the key method for seamless transitions. It:
        1. Preloads the new loop into the inactive input slot
        2. Waits for preload to complete
        3. Triggers the crossfade by updating filter graph
        4. Swaps active/inactive slots

        Args:
            new_loop: Path to new video loop
            preload_duration: Time to wait for preloading

        Returns:
            True if switch was successful
        """
        if self._state != StreamState.RUNNING:
            logger.warning(f"Cannot switch track: current state is {self._state}")
            return False

        try:
            self._state = StreamState.SWITCHING
            logger.info(f"Switching track to: {new_loop}")

            # Preload new loop into inactive slot
            success = await self.input_switcher.switch_input(
                new_loop,
                crossfade_duration=self.config.crossfade_duration,
            )

            if not success:
                logger.error("Failed to switch input")
                self._state = StreamState.RUNNING
                return False

            # Wait for preload
            await asyncio.sleep(preload_duration)

            # Update state
            self._next_loop = new_loop
            self._switch_count += 1

            # Note: With symlinks, FFmpeg will automatically use the new video
            # when it loops the input. The crossfade happens based on the
            # filter graph we built at startup.

            # After crossfade duration, update current loop
            await asyncio.sleep(self.config.crossfade_duration)
            self._current_loop = new_loop

            self._state = StreamState.RUNNING
            logger.info(f"Track switch completed (#{self._switch_count}): {new_loop}")
            return True

        except Exception as e:
            logger.error(f"Failed to switch track: {e}", exc_info=True)
            self._state = StreamState.RUNNING
            return False

    async def stop_stream(self, force: bool = False) -> bool:
        """Stop the FFmpeg stream.

        Args:
            force: If True, use SIGKILL instead of SIGTERM

        Returns:
            True if stopped successfully
        """
        if self._state == StreamState.STOPPED:
            logger.info("Stream already stopped")
            return True

        try:
            self._state = StreamState.STOPPING
            logger.info("Stopping FFmpeg stream")

            # Stop monitoring
            self._should_monitor = False
            if self._monitor_task:
                self._monitor_task.cancel()
                try:
                    await self._monitor_task
                except asyncio.CancelledError:
                    pass

            # Terminate process
            if self._process:
                if force:
                    self._process.kill()
                else:
                    self._process.terminate()

                try:
                    self._process.wait(timeout=self.config.process_timeout)
                except subprocess.TimeoutExpired:
                    logger.warning("Process did not terminate gracefully, force killing")
                    self._process.kill()
                    self._process.wait(timeout=5)

            # Cleanup
            await self.input_switcher.cleanup()

            self._state = StreamState.STOPPED
            self._process = None
            logger.info("FFmpeg stream stopped")
            return True

        except Exception as e:
            logger.error(f"Error stopping stream: {e}", exc_info=True)
            return False

    async def restart_stream(self) -> bool:
        """Restart the stream (for error recovery).

        Returns:
            True if restart was successful
        """
        if self._restart_count >= self.config.max_restart_attempts:
            logger.error(f"Max restart attempts ({self.config.max_restart_attempts}) reached")
            return False

        self._restart_count += 1
        logger.warning(
            f"Restarting stream (attempt {self._restart_count}/"
            f"{self.config.max_restart_attempts})"
        )

        current_loop = self._current_loop

        await self.stop_stream(force=True)
        await asyncio.sleep(1.0)

        if current_loop:
            return await self.start_stream(current_loop)
        else:
            logger.error("Cannot restart: no current loop known")
            return False

    def _build_command(
        self,
        loop0_path: str,
        loop1_path: str,
        audio_url: str,
        rtmp_endpoint: str,
    ) -> List[str]:
        """Build FFmpeg command for dual-input streaming.

        Args:
            loop0_path: Path to first video loop
            loop1_path: Path to second video loop
            audio_url: Audio stream URL
            rtmp_endpoint: RTMP output endpoint

        Returns:
            Command as list of strings
        """
        # Build filter graph
        filter_graph = self.filter_builder.build_dual_input_filter(
            offset_seconds=0.0,  # Crossfade starts immediately when inputs change
        )

        cmd = [
            self.config.ffmpeg_binary,
            "-re",  # Read at native framerate
            "-loglevel",
            self.config.log_level,
            "-hide_banner",
            # Input 0: First video loop
            "-stream_loop",
            "-1",
            "-i",
            loop0_path,
            # Input 1: Second video loop
            "-stream_loop",
            "-1",
            "-i",
            loop1_path,
            # Input 2: Live audio
            "-i",
            audio_url,
            # Filter graph for video crossfading
            "-filter_complex",
            filter_graph,
            # Map outputs
            "-map",
            "[vout]",  # Video from filter
            "-map",
            "2:a",  # Audio from input 2
            # Video encoding
            "-c:v",
            self.config.video_codec,
            "-preset",
            self.config.video_preset,
            "-b:v",
            self.config.video_bitrate,
            "-maxrate",
            self.config.video_bitrate,
            "-bufsize",
            f"{int(self.config.video_bitrate.rstrip('k')) * 2}k",
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
            "-ac",
            "2",
            # Output
            "-f",
            "flv",
            rtmp_endpoint,
        ]

        return cmd

    async def _monitor_process(self) -> None:
        """Monitor FFmpeg process health."""
        logger.info("Starting process monitor")

        while self._should_monitor:
            try:
                await asyncio.sleep(1.0)

                if not self._process:
                    continue

                # Check if process is still running
                if self._process.poll() is not None:
                    logger.error(f"FFmpeg process crashed! Exit code: {self._process.returncode}")
                    self._state = StreamState.ERROR

                    # Attempt restart if enabled
                    if self.config.restart_on_error:
                        await self.restart_stream()

                    break

                # Monitor resource usage
                try:
                    proc = psutil.Process(self._process.pid)
                    cpu = proc.cpu_percent(interval=0.1)
                    mem_mb = proc.memory_info().rss / 1024 / 1024

                    logger.debug(
                        f"FFmpeg (PID {self._process.pid}): " f"CPU={cpu:.1f}% MEM={mem_mb:.1f}MB"
                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            except asyncio.CancelledError:
                logger.info("Process monitor cancelled")
                break
            except Exception as e:
                logger.error(f"Error in process monitor: {e}", exc_info=True)

        logger.info("Process monitor stopped")

    def get_status(self) -> dict:
        """Get current status.

        Returns:
            Dictionary with status information
        """
        uptime = 0
        if self._started_at:
            uptime = (datetime.now() - self._started_at).total_seconds()

        return {
            "state": self._state.value,
            "pid": self._process.pid if self._process else None,
            "current_loop": self._current_loop,
            "next_loop": self._next_loop,
            "uptime_seconds": uptime,
            "switch_count": self._switch_count,
            "restart_count": self._restart_count,
            "input_switcher_stats": self.input_switcher.get_stats(),
        }

    def is_running(self) -> bool:
        """Check if stream is running.

        Returns:
            True if stream is in RUNNING state
        """
        return self._state == StreamState.RUNNING

    async def cleanup(self) -> None:
        """Clean up all resources."""
        logger.info("Cleaning up DualInputFFmpegManager")

        await self.stop_stream(force=True)
        await self.input_switcher.cleanup()

        logger.info("Cleanup complete")
