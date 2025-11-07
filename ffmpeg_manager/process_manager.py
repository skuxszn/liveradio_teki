"""
FFmpeg process manager.

Manages FFmpeg process lifecycle with graceful handovers, auto-recovery,
and real-time monitoring.
"""

import asyncio
import logging
import signal
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Optional

import psutil

from ffmpeg_manager.command_builder import FFmpegCommandBuilder
from ffmpeg_manager.config import FFmpegConfig
from ffmpeg_manager.log_parser import FFmpegLogParser

logger = logging.getLogger(__name__)


class ProcessState(str, Enum):
    """FFmpeg process states."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    CRASHED = "crashed"
    RESTARTING = "restarting"


@dataclass
class ProcessInfo:
    """Information about a running FFmpeg process."""

    pid: int
    state: ProcessState
    loop_path: str
    started_at: datetime
    restart_count: int = 0
    process: Optional[subprocess.Popen] = None
    log_parser: Optional[FFmpegLogParser] = None


class FFmpegProcessManager:
    """
    Manages FFmpeg process lifecycle with automatic recovery and graceful transitions.

    Features:
    - Spawn FFmpeg processes with real-time log monitoring
    - Graceful overlap during track switches (spawn new → wait → kill old)
    - Auto-restart on crashes (with max retry limit)
    - Zombie process cleanup
    - Thread-safe process tracking
    """

    def __init__(
        self,
        config: Optional[FFmpegConfig] = None,
        command_builder: Optional[FFmpegCommandBuilder] = None,
    ):
        """
        Initialize process manager.

        Args:
            config: FFmpeg configuration (creates default if not provided)
            command_builder: Command builder instance (creates default if not provided)
        """
        if config is None:
            from ffmpeg_manager.config import get_config

            config = get_config()

        self.config = config

        if command_builder is None:
            command_builder = FFmpegCommandBuilder(config)

        self.command_builder = command_builder

        # Process tracking
        self._current_process: Optional[ProcessInfo] = None
        self._previous_process: Optional[ProcessInfo] = None
        self._lock = asyncio.Lock()

        # Monitoring
        self._monitor_task: Optional[asyncio.Task] = None
        self._should_monitor = False

        logger.info("FFmpeg Process Manager initialized")

    async def start_stream(
        self,
        loop_path: str,
        audio_url: Optional[str] = None,
        rtmp_endpoint: Optional[str] = None,
    ) -> bool:
        """
        Start FFmpeg stream with the specified video loop.

        Args:
            loop_path: Absolute path to video loop file
            audio_url: Optional audio stream URL (uses config default if not provided)
            rtmp_endpoint: Optional RTMP endpoint (uses config default if not provided)

        Returns:
            True if stream started successfully, False otherwise
        """
        async with self._lock:
            try:
                # Build FFmpeg command
                cmd = self.command_builder.build_command(
                    loop_path=loop_path,
                    audio_url=audio_url,
                    rtmp_endpoint=rtmp_endpoint,
                    fade_in=True,
                )

                logger.info(f"Starting FFmpeg stream: {loop_path}")
                logger.debug(f"Command: {' '.join(cmd)}")

                # Spawn FFmpeg process
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.DEVNULL,
                    preexec_fn=None,  # Don't change process group on Linux
                )

                # Create process info
                log_parser = FFmpegLogParser()
                process_info = ProcessInfo(
                    pid=process.pid,
                    state=ProcessState.STARTING,
                    loop_path=loop_path,
                    started_at=datetime.now(),
                    process=process,
                    log_parser=log_parser,
                )

                self._current_process = process_info

                # Start monitoring in background
                if not self._should_monitor:
                    self._should_monitor = True
                    self._monitor_task = asyncio.create_task(self._monitor_process())

                # Wait briefly to ensure process starts
                await asyncio.sleep(0.5)

                # Check if process is still running
                if process.poll() is None:
                    process_info.state = ProcessState.RUNNING
                    logger.info(f"FFmpeg stream started successfully (PID: {process.pid})")
                    return True
                else:
                    # Process died immediately
                    stderr = process.stderr.read().decode("utf-8", errors="replace")
                    logger.error(f"FFmpeg process died immediately: {stderr[:500]}")
                    process_info.state = ProcessState.CRASHED
                    return False

            except Exception as e:
                logger.error(f"Failed to start FFmpeg stream: {e}", exc_info=True)
                return False

    async def switch_track(
        self,
        new_loop_path: str,
        audio_url: Optional[str] = None,
        rtmp_endpoint: Optional[str] = None,
    ) -> bool:
        """
        Switch to a new track with graceful overlap.

        Process:
        1. Spawn new FFmpeg process with new loop
        2. Wait for overlap duration
        3. Terminate old process
        4. Monitor transition

        Args:
            new_loop_path: Path to new video loop
            audio_url: Optional audio stream URL
            rtmp_endpoint: Optional RTMP endpoint

        Returns:
            True if switch was successful, False otherwise
        """
        async with self._lock:
            try:
                logger.info(f"Switching track to: {new_loop_path}")

                # Build command for new process
                cmd = self.command_builder.build_command(
                    loop_path=new_loop_path,
                    audio_url=audio_url,
                    rtmp_endpoint=rtmp_endpoint,
                    fade_in=True,
                )

                # Spawn new process
                new_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.DEVNULL,
                )

                log_parser = FFmpegLogParser()
                new_process_info = ProcessInfo(
                    pid=new_process.pid,
                    state=ProcessState.STARTING,
                    loop_path=new_loop_path,
                    started_at=datetime.now(),
                    process=new_process,
                    log_parser=log_parser,
                )

                logger.info(
                    f"New FFmpeg process spawned (PID: {new_process.pid}), "
                    f"overlap duration: {self.config.overlap_duration}s"
                )

                # Wait for overlap duration (allows fade-in and buffering)
                await asyncio.sleep(self.config.overlap_duration)

                # Terminate old process
                old_process_info = self._current_process
                if old_process_info and old_process_info.process:
                    await self._terminate_process(old_process_info)
                    self._previous_process = old_process_info

                # Update current process
                self._current_process = new_process_info

                # Check if new process is still running
                if new_process.poll() is None:
                    new_process_info.state = ProcessState.RUNNING
                    logger.info("Track switch completed successfully")
                    return True
                else:
                    stderr = new_process.stderr.read().decode("utf-8", errors="replace")
                    logger.error(f"New FFmpeg process died during switch: {stderr[:500]}")
                    new_process_info.state = ProcessState.CRASHED

                    # Try to recover by restarting old process if available
                    if old_process_info:
                        logger.warning("Attempting to recover previous process")
                        await self._recover_process(old_process_info)

                    return False

            except Exception as e:
                logger.error(f"Failed to switch track: {e}", exc_info=True)
                return False

    async def stop_stream(self, force: bool = False) -> bool:
        """
        Stop the current FFmpeg stream.

        Args:
            force: If True, use SIGKILL instead of SIGTERM

        Returns:
            True if stopped successfully, False otherwise
        """
        async with self._lock:
            if not self._current_process:
                logger.info("No active stream to stop")
                return True

            try:
                logger.info(f"Stopping FFmpeg stream (PID: {self._current_process.pid})")
                success = await self._terminate_process(self._current_process, force)

                if success:
                    self._previous_process = self._current_process
                    self._current_process = None
                    logger.info("FFmpeg stream stopped")

                return success

            except Exception as e:
                logger.error(f"Failed to stop stream: {e}", exc_info=True)
                return False

    async def restart_stream(self) -> bool:
        """
        Restart the current stream (useful for recovery).

        Returns:
            True if restarted successfully, False otherwise
        """
        if not self._current_process:
            logger.warning("No active stream to restart")
            return False

        loop_path = self._current_process.loop_path
        logger.info(f"Restarting FFmpeg stream with loop: {loop_path}")

        # Stop current stream
        await self.stop_stream()

        # Start new stream
        return await self.start_stream(loop_path)

    async def _terminate_process(
        self,
        process_info: ProcessInfo,
        force: bool = False,
    ) -> bool:
        """
        Terminate an FFmpeg process gracefully or forcefully.

        Args:
            process_info: Process information
            force: Use SIGKILL instead of SIGTERM

        Returns:
            True if terminated successfully
        """
        if not process_info.process:
            return True

        process = process_info.process
        process_info.state = ProcessState.STOPPING

        try:
            # Check if process is still running
            if process.poll() is not None:
                logger.debug(f"Process {process.pid} already terminated")
                return True

            # Send termination signal
            if force:
                logger.warning(f"Force killing process {process.pid}")
                process.kill()  # SIGKILL
            else:
                logger.debug(f"Gracefully terminating process {process.pid}")
                process.terminate()  # SIGTERM

            # Wait for process to terminate
            try:
                process.wait(timeout=self.config.process_timeout)
                logger.debug(f"Process {process.pid} terminated successfully")
                process_info.state = ProcessState.STOPPED
                return True

            except subprocess.TimeoutExpired:
                logger.warning(f"Process {process.pid} did not terminate gracefully, force killing")
                process.kill()
                process.wait(timeout=5)
                process_info.state = ProcessState.STOPPED
                return True

        except Exception as e:
            logger.error(f"Error terminating process {process.pid}: {e}")
            return False

    async def _recover_process(self, process_info: ProcessInfo) -> bool:
        """
        Attempt to recover a crashed process.

        Args:
            process_info: Process information

        Returns:
            True if recovery successful
        """
        if process_info.restart_count >= self.config.max_restart_attempts:
            logger.error(
                f"Max restart attempts ({self.config.max_restart_attempts}) "
                f"reached for {process_info.loop_path}"
            )
            return False

        process_info.restart_count += 1
        process_info.state = ProcessState.RESTARTING

        logger.warning(
            f"Attempting to recover process (attempt {process_info.restart_count}/"
            f"{self.config.max_restart_attempts})"
        )

        return await self.start_stream(process_info.loop_path)

    async def _monitor_process(self) -> None:
        """Monitor FFmpeg process health in background."""
        logger.info("Starting process monitor")

        while self._should_monitor:
            try:
                await asyncio.sleep(1.0)  # Check every second

                async with self._lock:
                    if not self._current_process:
                        continue

                    process_info = self._current_process
                    process = process_info.process

                    if not process:
                        continue

                    # Check if process is still running
                    if process.poll() is not None:
                        logger.error(
                            f"FFmpeg process {process.pid} crashed! "
                            f"Exit code: {process.returncode}"
                        )

                        # Read stderr for error info
                        if process.stderr:
                            stderr = process.stderr.read().decode("utf-8", errors="replace")
                            logger.error(f"FFmpeg stderr: {stderr[-1000:]}")  # Last 1000 chars

                        process_info.state = ProcessState.CRASHED

                        # Attempt recovery
                        await self._recover_process(process_info)
                        continue

                    # Read and parse stderr (non-blocking)
                    if process.stderr:
                        try:
                            # Set non-blocking mode
                            import fcntl
                            import os

                            fd = process.stderr.fileno()
                            fl = fcntl.fcntl(fd, fcntl.F_GETFL)
                            fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

                            # Read available data
                            try:
                                data = process.stderr.read()
                                if data:
                                    lines = data.decode("utf-8", errors="replace").split("\n")
                                    for line in lines:
                                        if line.strip() and process_info.log_parser:
                                            error = process_info.log_parser.parse_line(line)
                                            if error:
                                                logger.warning(
                                                    f"FFmpeg {error.level}: {error.message}"
                                                )
                            except BlockingIOError:
                                # No data available
                                pass

                        except Exception as e:
                            logger.debug(f"Error reading stderr: {e}")

                    # Check process resource usage
                    try:
                        proc = psutil.Process(process.pid)
                        cpu_percent = proc.cpu_percent(interval=0.1)
                        memory_mb = proc.memory_info().rss / 1024 / 1024

                        logger.debug(
                            f"Process {process.pid}: CPU={cpu_percent:.1f}% "
                            f"MEM={memory_mb:.1f}MB"
                        )

                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

            except asyncio.CancelledError:
                logger.info("Process monitor cancelled")
                break
            except Exception as e:
                logger.error(f"Error in process monitor: {e}", exc_info=True)

        logger.info("Process monitor stopped")

    async def cleanup(self) -> None:
        """Clean up resources and stop all processes."""
        logger.info("Cleaning up FFmpeg process manager")

        # Stop monitoring
        self._should_monitor = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        # Stop current process
        if self._current_process:
            await self.stop_stream(force=True)

        logger.info("Cleanup complete")

    def get_status(self) -> Dict:
        """
        Get current status of FFmpeg process.

        Returns:
            Dictionary with process status information
        """
        if not self._current_process:
            return {
                "state": ProcessState.STOPPED,
                "pid": None,
                "loop_path": None,
                "uptime_seconds": 0,
                "restart_count": 0,
            }

        uptime = (datetime.now() - self._current_process.started_at).total_seconds()

        status = {
            "state": self._current_process.state,
            "pid": self._current_process.pid,
            "loop_path": self._current_process.loop_path,
            "uptime_seconds": uptime,
            "restart_count": self._current_process.restart_count,
        }

        # Add metrics if available
        if self._current_process.log_parser:
            status["metrics"] = self._current_process.log_parser.get_metrics_summary()

        return status

    def is_running(self) -> bool:
        """
        Check if FFmpeg process is currently running.

        Returns:
            True if process is running
        """
        return (
            self._current_process is not None
            and self._current_process.state == ProcessState.RUNNING
        )
