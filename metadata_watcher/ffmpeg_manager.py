"""FFmpeg process manager with graceful handovers and auto-recovery.

Manages FFmpeg process lifecycle including spawning, monitoring, and
graceful transitions between tracks with overlap.
"""

import asyncio
import json
import logging
import socket
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import aiohttp

from .config import Config

logger = logging.getLogger(__name__)


class FFmpegProcess:
    """Represents a single FFmpeg process instance."""

    def __init__(
        self,
        process: subprocess.Popen,
        track_key: str,
        loop_path: Path,
        started_at: datetime,
        log_file: Optional[Path] = None,
        log_handle: Optional[object] = None,
    ):
        """Initialize FFmpeg process wrapper.

        Args:
            process: The subprocess.Popen instance.
            track_key: Track identifier (artist - title).
            loop_path: Path to video loop file.
            started_at: Timestamp when process started.
            log_file: Path to FFmpeg log file.
            log_handle: Open file handle for logging.
        """
        self.process = process
        self.track_key = track_key
        self.loop_path = loop_path
        self.started_at = started_at
        self.pid = process.pid
        self.log_file = log_file
        self.log_handle = log_handle

    @property
    def is_running(self) -> bool:
        """Check if process is still running.

        Returns:
            bool: True if process is running, False otherwise.
        """
        return self.process.poll() is None

    @property
    def uptime_seconds(self) -> float:
        """Get process uptime in seconds.

        Returns:
            float: Uptime in seconds.
        """
        return (datetime.now() - self.started_at).total_seconds()

    def terminate(self) -> None:
        """Gracefully terminate the process (SIGTERM)."""
        if self.is_running:
            logger.info(f"Sending SIGTERM to FFmpeg process {self.pid}")
            self.process.terminate()

        # Close log handle
        if self.log_handle:
            try:
                self.log_handle.close()
            except Exception:
                pass

    def kill(self) -> None:
        """Forcefully kill the process (SIGKILL)."""
        if self.is_running:
            logger.warning(f"Sending SIGKILL to FFmpeg process {self.pid}")
            self.process.kill()

    def wait(self, timeout: Optional[float] = None) -> Optional[int]:
        """Wait for process to exit.

        Args:
            timeout: Maximum time to wait in seconds.

        Returns:
            Exit code if process exited, None if timeout.
        """
        try:
            return self.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            return None


class FFmpegManager:
    """Manages FFmpeg process lifecycle with graceful handovers."""

    def __init__(self, config: Config):
        """Initialize FFmpeg manager.

        Args:
            config: Application configuration.
        """
        self.config = config
        self.current_process: Optional[FFmpegProcess] = None
        self.process_lock = asyncio.Lock()
        self.restart_attempts: Dict[str, int] = {}
        self.last_restart_time: Dict[str, float] = {}
        self.last_error: Optional[str] = None

        # Shared volume paths for dashboard integration
        self.control_dir = Path("/app/stream")
        self.status_file = self.control_dir / "status.json"
        self.control_file = self.control_dir / "control.json"

        # Log directory for FFmpeg output
        self.log_dir = Path("/var/log/radio")

        # Ensure directories exist
        try:
            self.control_dir.mkdir(parents=True, exist_ok=True)
            self.log_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Control directory initialized: {self.control_dir}")
            logger.info(f"Log directory initialized: {self.log_dir}")
        except Exception as e:
            logger.warning(f"Failed to create directories: {e}")

    async def switch_track(
        self,
        track_key: str,
        artist: str,
        title: str,
        loop_path: Path,
        skip_cooldown: bool = True,
    ) -> bool:
        """Switch to a new track.

        Terminates old FFmpeg process, then spawns new one.
        Note: nginx-rtmp doesn't support overlapping publishers, so we must
        stop the old stream before starting the new one.

        Args:
            track_key: Normalized track identifier.
            artist: Artist name.
            title: Song title.
            loop_path: Path to video loop file.
            skip_cooldown: If True, bypass restart cooldown (for webhook triggers).

        Returns:
            bool: True if switch successful, False otherwise.
        """
        async with self.process_lock:
            logger.info(f"Starting track switch to: {track_key}")

            # Gracefully terminate old process FIRST (nginx-rtmp doesn't allow overlapping publishers)
            if self.current_process and self.current_process.is_running:
                old_pid = self.current_process.pid
                old_track = self.current_process.track_key
                logger.info(f"Terminating old stream: {old_track} (PID: {old_pid})")
                self.current_process.terminate()

                # Wait up to 3 seconds for graceful termination
                exit_code = self.current_process.wait(timeout=3.0)
                if exit_code is None:
                    # Process didn't exit, force kill
                    logger.warning(f"Old process {old_pid} didn't exit gracefully, killing")
                    self.current_process.kill()
                    self.current_process.wait(timeout=2.0)

                # Give nginx-rtmp a moment to clean up the connection
                await asyncio.sleep(0.5)

            # Build FFmpeg command for new track
            cmd = self._build_ffmpeg_command(loop_path, artist, title)

            # Spawn new process (with optional cooldown bypass for webhooks)
            new_process = await self._spawn_process(
                track_key, loop_path, cmd, skip_cooldown=skip_cooldown
            )
            if not new_process:
                logger.error(f"Failed to spawn FFmpeg process for {track_key}")
                return False

            # Set new process as current
            self.current_process = new_process
            logger.info(
                f"Track switch complete: {track_key} (PID: {new_process.pid}, "
                f"loop: {loop_path.name})"
            )

            # Update status file for dashboard
            self.update_status_file()

            return True

    async def _spawn_process(
        self,
        track_key: str,
        loop_path: Path,
        cmd: List[str],
        skip_cooldown: bool = False,
    ) -> Optional[FFmpegProcess]:
        """Spawn a new FFmpeg process with proper logging.

        Args:
            track_key: Track identifier.
            loop_path: Path to video loop.
            cmd: FFmpeg command arguments.
            skip_cooldown: If True, bypass restart cooldown (for webhook triggers).

        Returns:
            FFmpegProcess if successful, None otherwise.
        """
        # Get current attempt count
        attempts = self.restart_attempts.get(track_key, 0)

        # Check restart cooldown (only for automatic restarts, not webhooks)
        if not skip_cooldown:
            if not self._check_restart_cooldown(track_key):
                logger.error(f"Restart cooldown active for {track_key}")
                return None

            # Check restart attempts (only for automatic restarts)
            if attempts >= self.config.max_restart_attempts:
                logger.error(
                    f"Max restart attempts ({self.config.max_restart_attempts}) "
                    f"exceeded for {track_key}"
                )
                return None
        else:
            # Reset cooldown timer for webhook-triggered switches
            self.restart_attempts[track_key] = 0
            attempts = 0

        try:
            # Create log file for this stream session
            log_file = self.log_dir / f"ffmpeg_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

            # Open log file for FFmpeg stderr/stdout
            log_handle = open(log_file, "w")

            # Spawn process with stderr/stdout to log file
            process = subprocess.Popen(
                cmd,
                stdout=log_handle,
                stderr=subprocess.STDOUT,  # Redirect stderr to stdout
                stdin=subprocess.DEVNULL,
            )

            # Wait a moment to ensure it starts
            await asyncio.sleep(0.5)

            # Check if process started successfully
            if process.poll() is not None:
                # Process already exited - read the error
                log_handle.close()
                with open(log_file, "r") as f:
                    error_output = f.read()

                logger.error(f"FFmpeg process exited immediately. Error output:\n{error_output}")

                # Write error to status file for dashboard visibility
                self.last_error = error_output[-500:] if len(error_output) > 500 else error_output
                self.update_status_file()

                return None

            # Create wrapper with log file reference
            ffmpeg_process = FFmpegProcess(
                process=process,
                track_key=track_key,
                loop_path=loop_path,
                started_at=datetime.now(),
                log_file=log_file,
                log_handle=log_handle,
            )

            # Update restart tracking
            self.restart_attempts[track_key] = attempts + 1
            self.last_restart_time[track_key] = time.time()

            logger.info(f"FFmpeg process spawned: PID {ffmpeg_process.pid}, log: {log_file}")
            return ffmpeg_process

        except Exception as e:
            logger.error(f"Failed to spawn FFmpeg process: {e}", exc_info=True)
            return None

    def _build_ffmpeg_command(
        self,
        loop_path: Path,
        artist: str,
        title: str,
    ) -> List[str]:
        """Build FFmpeg command for streaming.

        Args:
            loop_path: Path to video loop file.
            artist: Artist name (for logging).
            title: Song title (for logging).

        Returns:
            List of command arguments.
        """
        # Parse resolution
        width, height = self.config.video_resolution.split(":")

        # Check if logo is enabled
        enable_logo = getattr(self.config, "enable_logo_watermark", False)
        if enable_logo and isinstance(enable_logo, str):
            enable_logo = enable_logo.lower() == "true"

        # Build base command
        cmd = [
            "ffmpeg",
            "-re",  # Read input at native frame rate
            "-stream_loop",
            "-1",  # Loop video infinitely
            "-i",
            str(loop_path),  # Video input
            "-i",
            self.config.azuracast_audio_url,  # Audio input from AzuraCast
        ]

        # Add logo as third input if enabled
        if enable_logo:
            logo_path = getattr(self.config, "logo_path", "/app/logos/logo.png")
            cmd.extend(["-loop", "1", "-i", logo_path])
            # When using filter_complex, we don't map here - we map after the filter
        else:
            # No logo, map video and audio normally
            cmd.extend(
                [
                    "-map",
                    "0:v",  # Map video from first input
                    "-map",
                    "1:a",  # Map audio from second input
                ]
            )

        # Video filters
        filters = []

        # Add fade if configured
        if self.config.fade_duration > 0:
            filters.append(f"fade=t=in:st=0:d={self.config.fade_duration}")

        # Scale to target resolution
        filters.append(f"scale={width}:{height}")

        # Add text overlay - Now Playing info (if enabled)
        # Check if text overlay is enabled (default: false for better performance)
        enable_overlay = getattr(self.config, "enable_text_overlay", False)

        if enable_overlay and isinstance(enable_overlay, str):
            enable_overlay = enable_overlay.lower() == "true"

        if enable_overlay:
            # Escape single quotes and special characters in text
            artist_escaped = artist.replace("'", "'\\\\\\''").replace(":", "\\:")
            title_escaped = title.replace("'", "'\\\\\\''").replace(":", "\\:")

            # Position: bottom center, with semi-transparent black background
            text_filter = (
                f"drawtext="
                f"text='Now Playing\\:':"
                f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
                f"fontsize=32:"
                f"fontcolor=white:"
                f"x=(w-text_w)/2:"
                f"y=h-120:"
                f"box=1:boxcolor=black@0.6:boxborderw=10,"
                f"drawtext="
                f"text='{artist_escaped} - {title_escaped}':"
                f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
                f"fontsize=28:"
                f"fontcolor=white:"
                f"x=(w-text_w)/2:"
                f"y=h-70:"
                f"box=1:boxcolor=black@0.6:boxborderw=10"
            )
            filters.append(text_filter)

        # Pixel format for compatibility
        filters.append("format=yuv420p")

        # Build the video filter
        vf_string = ",".join(filters)

        # Add logo watermark if enabled (uses filter_complex)
        if enable_logo:
            logo_opacity = getattr(self.config, "logo_opacity", 0.8)

            # Use filter_complex for full-frame logo overlay
            # Input 0: video loop, Input 1: audio, Input 2: logo
            # Scale logo to match video resolution, then overlay
            filter_complex = (
                f"[0:v]{vf_string}[v0];"
                f"[2:v]scale={width}:{height},format=rgba,colorchannelmixer=aa={logo_opacity}[logo];"
                f"[v0][logo]overlay=0:0[vout]"  # Output to [vout] stream
            )
            cmd.extend(
                [
                    "-filter_complex",
                    filter_complex,
                    "-map",
                    "[vout]",  # Map the filter output as video
                    "-map",
                    "1:a",  # Map audio from second input
                ]
            )
        else:
            # No logo, use simple video filter
            cmd.extend(["-vf", vf_string])

        # Video encoding
        cmd.extend(
            [
                "-c:v",
                self.config.video_encoder,
                "-preset",
                self.config.ffmpeg_preset,
                "-g",
                "50",  # GOP size (keyframe interval)
                "-keyint_min",
                "50",  # Minimum keyframe interval
                "-b:v",
                self.config.video_bitrate,
                "-maxrate",
                self.config.video_bitrate,
                "-bufsize",
                f"{int(self.config.video_bitrate.rstrip('k')) * 2}k",
                "-pix_fmt",
                "yuv420p",
            ]
        )

        # Audio encoding
        cmd.extend(
            [
                "-c:a",
                "aac",
                "-b:a",
                self.config.audio_bitrate,
                "-ar",
                "44100",  # Sample rate
                "-ac",
                "2",  # Stereo
            ]
        )

        # Audio fade-in
        cmd.extend(
            [
                "-af",
                f"afade=t=in:ss=0:d={self.config.fade_duration}",
            ]
        )

        # Output format and destination
        cmd.extend(
            [
                "-f",
                "flv",
                self.config.rtmp_endpoint,
            ]
        )

        # Logging
        log_level = self.config.ffmpeg_log_level
        cmd.extend(["-loglevel", log_level])

        # Log command (redact sensitive info)
        cmd_str = " ".join(cmd)
        logger.debug(f"FFmpeg command: {cmd_str[:200]}...")

        return cmd

    def _check_restart_cooldown(self, track_key: str) -> bool:
        """Check if restart cooldown period has passed.

        Args:
            track_key: Track identifier.

        Returns:
            bool: True if cooldown passed or first attempt, False otherwise.
        """
        if track_key not in self.last_restart_time:
            return True

        elapsed = time.time() - self.last_restart_time[track_key]
        cooldown = self.config.restart_cooldown_seconds

        if elapsed < cooldown:
            logger.warning(
                f"Restart cooldown active for {track_key}: " f"{cooldown - elapsed:.1f}s remaining"
            )
            return False

        # Cooldown passed, reset attempts counter
        self.restart_attempts[track_key] = 0
        return True

    def get_status(self) -> Dict:
        """Get current FFmpeg process status.

        Returns:
            dict: Status information.
        """
        if not self.current_process:
            return {
                "status": "stopped",
                "process": None,
            }

        return {
            "status": "running" if self.current_process.is_running else "crashed",
            "process": {
                "pid": self.current_process.pid,
                "track_key": self.current_process.track_key,
                "loop_path": str(self.current_process.loop_path),
                "uptime_seconds": self.current_process.uptime_seconds,
                "started_at": self.current_process.started_at.isoformat(),
            },
        }

    def update_status_file(self) -> None:
        """Write current status to shared status file for dashboard integration."""
        try:
            status_data = {
                "running": bool(self.current_process and self.current_process.is_running),
                "timestamp": datetime.now().isoformat(),
            }

            if self.current_process and self.current_process.is_running:
                # Parse artist and title from track_key (format: "artist - title")
                track_parts = self.current_process.track_key.split(" - ", 1)
                artist = track_parts[0] if len(track_parts) > 0 else "Unknown"
                title = track_parts[1] if len(track_parts) > 1 else "Unknown"

                status_data.update(
                    {
                        "pid": self.current_process.pid,
                        "current_track": {
                            "artist": artist,
                            "title": title,
                            "track_key": self.current_process.track_key,
                            "uptime_seconds": int(self.current_process.uptime_seconds),
                        },
                        "started_at": self.current_process.started_at.isoformat(),
                    }
                )
            else:
                status_data["current_track"] = None
                status_data["pid"] = None
                status_data["started_at"] = None

                # Add last error if available
                if self.last_error:
                    status_data["last_error"] = self.last_error

            # Write atomically by writing to temp file then renaming
            temp_file = self.status_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(status_data, f, indent=2)
            temp_file.replace(self.status_file)

        except Exception as e:
            logger.error(f"Failed to update status file: {e}", exc_info=True)

    async def check_control_commands(self) -> None:
        """Check for control commands from dashboard and execute them."""
        if not self.control_file.exists():
            return

        try:
            # Read and parse command
            with open(self.control_file, "r") as f:
                command = json.load(f)

            action = command.get("action")
            logger.info(f"Received control command: {action}")

            # Execute command based on action
            if action == "start":
                # Start stream from stopped state
                if self.current_process and self.current_process.is_running:
                    logger.warning("Cannot start: stream is already running")
                else:
                    # Validate configuration before starting
                    validation_errors = []

                    # Check default loop exists
                    if not self.config.default_loop.exists():
                        validation_errors.append(
                            f"Default loop file not found: {self.config.default_loop}"
                        )

                    # Check audio URL is reachable
                    try:
                        timeout = aiohttp.ClientTimeout(total=5)
                        async with aiohttp.ClientSession(timeout=timeout) as session:
                            async with session.head(self.config.azuracast_audio_url) as resp:
                                if resp.status >= 400:
                                    validation_errors.append(
                                        f"Audio source unreachable (HTTP {resp.status}): {self.config.azuracast_audio_url}"
                                    )
                    except Exception as e:
                        validation_errors.append(f"Cannot reach audio source: {e}")

                    # Check RTMP endpoint connectivity
                    try:
                        # Parse RTMP URL: rtmp://host:port/path
                        rtmp_parts = self.config.rtmp_endpoint.split("//")[1].split("/")
                        host_port = rtmp_parts[0]
                        if ":" in host_port:
                            rtmp_host, rtmp_port = host_port.split(":")
                            rtmp_port = int(rtmp_port)
                        else:
                            rtmp_host = host_port
                            rtmp_port = 1935  # Default RTMP port

                        # Basic TCP check
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(2)
                        result = sock.connect_ex((rtmp_host, rtmp_port))
                        sock.close()
                        if result != 0:
                            validation_errors.append(
                                f"RTMP server not reachable: {self.config.rtmp_endpoint}"
                            )
                    except Exception as e:
                        validation_errors.append(f"RTMP connectivity check failed: {e}")

                    if validation_errors:
                        # Write errors to status file
                        self.last_error = "; ".join(validation_errors)
                        self.update_status_file()
                        logger.error(f"Stream start validation failed: {validation_errors}")
                        self.control_file.unlink()
                        return

                    # Validation passed, start stream
                    artist = command.get("artist", "Radio")
                    title = command.get("title", "Stream")

                    # Use default loop for starting
                    loop_path = self.config.default_loop
                    track_key = f"{artist} - {title}"

                    # Build FFmpeg command and spawn process
                    cmd = self._build_ffmpeg_command(loop_path, artist, title)
                    new_process = await self._spawn_process(track_key, loop_path, cmd)

                    if new_process:
                        self.current_process = new_process
                        self.last_error = None  # Clear any previous errors
                        self.update_status_file()
                        logger.info(f"Stream started via dashboard command: {artist} - {title}")
                    else:
                        logger.error("Failed to start stream")

            elif action == "stop":
                await self.cleanup()
                logger.info("Stream stopped via dashboard command")

            elif action == "restart":
                # Get current track info before restart
                if self.current_process:
                    track_key = self.current_process.track_key
                    loop_path = self.current_process.loop_path
                    artist = command.get("artist", "Radio")
                    title = command.get("title", "Stream")

                    # Cleanup current process
                    await self.cleanup()
                    await asyncio.sleep(2)

                    # Start new process
                    cmd = self._build_ffmpeg_command(loop_path, artist, title)
                    new_process = await self._spawn_process(track_key, loop_path, cmd)

                    if new_process:
                        self.current_process = new_process
                        self.update_status_file()
                        logger.info("Stream restarted via dashboard command")
                    else:
                        logger.error("Failed to restart stream")
                else:
                    logger.warning("Cannot restart: no current process")

            # Remove command file after processing
            self.control_file.unlink()

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in control file: {e}")
            # Remove invalid command file
            try:
                self.control_file.unlink()
            except Exception:
                pass

        except Exception as e:
            logger.error(f"Error processing control command: {e}", exc_info=True)
            # Remove command file to prevent infinite loop
            try:
                self.control_file.unlink()
            except Exception:
                pass

    async def cleanup(self) -> None:
        """Clean up resources and terminate processes."""
        async with self.process_lock:
            if self.current_process and self.current_process.is_running:
                logger.info("Cleaning up: terminating FFmpeg process")
                self.current_process.terminate()
                self.current_process.wait(timeout=5.0)
                if self.current_process.is_running:
                    self.current_process.kill()
                    self.current_process.wait(timeout=2.0)

            # Clear current process and update status
            self.current_process = None
            self.update_status_file()
