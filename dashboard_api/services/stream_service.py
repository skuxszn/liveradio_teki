"""Stream control service logic."""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class StreamService:
    """Service for controlling the FFmpeg stream via shared volume communication."""

    def __init__(self):
        """Initialize stream service."""
        # Shared volume paths for communication with metadata watcher
        self.control_dir = Path("/app/stream")
        self.status_file = self.control_dir / "status.json"
        self.control_file = self.control_dir / "control.json"

        # Ensure control directory exists
        try:
            self.control_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"StreamService initialized with control directory: {self.control_dir}")
        except Exception as e:
            logger.warning(f"Failed to create control directory: {e}")
            logger.warning("Stream control may not work without shared volume")

    def get_status(self) -> dict:
        """Get current stream status from shared status file.

        Returns:
            dict: Stream status information.
        """
        try:
            # Check if status file exists
            if not self.status_file.exists():
                logger.debug("Status file does not exist, stream is stopped")
                return {
                    "status": "stopped",
                    "running": False,
                    "current_track": None,
                    "timestamp": datetime.utcnow().isoformat(),
                    "last_error": None,
                }

            # Read status from file
            with open(self.status_file, "r") as f:
                status_data = json.load(f)

            # Format response
            is_running = status_data.get("running", False)
            current_track = status_data.get("current_track")

            # Calculate uptime if available
            if current_track and "uptime_seconds" in current_track:
                # Uptime is already calculated by the stream process
                pass

            return {
                "status": "running" if is_running else "stopped",
                "running": is_running,
                "current_track": current_track,
                "timestamp": datetime.utcnow().isoformat(),
                "pid": status_data.get("pid"),
                "started_at": status_data.get("started_at"),
                "last_error": status_data.get("last_error"),  # Add error field
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse status file: {e}")
            return {
                "status": "error",
                "running": False,
                "current_track": None,
                "timestamp": datetime.utcnow().isoformat(),
                "message": "Failed to parse status file",
                "last_error": str(e),
            }
        except Exception as e:
            logger.error(f"Failed to read status: {e}", exc_info=True)
            return {
                "status": "unknown",
                "running": False,
                "current_track": None,
                "timestamp": datetime.utcnow().isoformat(),
                "message": f"Error reading status: {str(e)}",
                "last_error": str(e),
            }

    async def start_stream(self, artist: str = "Radio", title: str = "Stream") -> dict:
        """Start the FFmpeg stream by writing control command.

        Args:
            artist: Initial artist name.
            title: Initial title.

        Returns:
            dict: Start result.
        """
        try:
            # Check if already running
            status = self.get_status()
            if status.get("running"):
                return {"success": False, "message": "Stream is already running"}

            # Write start command to control file
            command = {
                "action": "start",
                "artist": artist,
                "title": title,
                "timestamp": datetime.utcnow().isoformat(),
            }

            with open(self.control_file, "w") as f:
                json.dump(command, f)

            logger.info(f"Sent start command: {artist} - {title}")

            # Wait up to 10 seconds for stream to start
            for i in range(20):
                await asyncio.sleep(0.5)
                status = self.get_status()
                if status.get("running"):
                    logger.info("Stream started successfully")
                    return {
                        "success": True,
                        "message": "Stream started successfully",
                        "status": status,
                    }

            # Timeout
            logger.warning("Stream start timeout - stream did not start within 10 seconds")
            return {
                "success": False,
                "message": "Stream start timeout - check stream logs for errors",
            }

        except Exception as e:
            logger.error(f"Failed to start stream: {e}", exc_info=True)
            return {"success": False, "message": f"Failed to start stream: {str(e)}"}

    async def stop_stream(self) -> dict:
        """Stop the FFmpeg stream by writing control command.

        Returns:
            dict: Stop result.
        """
        try:
            # Check if already stopped
            status = self.get_status()
            if not status.get("running"):
                return {"success": True, "message": "Stream is already stopped"}

            # Write stop command to control file
            command = {"action": "stop", "timestamp": datetime.utcnow().isoformat()}

            with open(self.control_file, "w") as f:
                json.dump(command, f)

            logger.info("Sent stop command")

            # Wait up to 10 seconds for stream to stop
            for i in range(20):
                await asyncio.sleep(0.5)
                status = self.get_status()
                if not status.get("running"):
                    logger.info("Stream stopped successfully")
                    return {"success": True, "message": "Stream stopped successfully"}

            # Timeout
            logger.warning("Stream stop timeout - stream did not stop within 10 seconds")
            return {
                "success": False,
                "message": "Stream stop timeout - stream may still be running",
            }

        except Exception as e:
            logger.error(f"Failed to stop stream: {e}", exc_info=True)
            return {"success": False, "message": f"Failed to stop stream: {str(e)}"}

    async def restart_stream(self) -> dict:
        """Restart the FFmpeg stream by writing control command.

        Returns:
            dict: Restart result.
        """
        try:
            # Get current track info
            status = self.get_status()
            current_track = status.get("current_track")

            # Extract artist and title
            artist = current_track.get("artist", "Radio") if current_track else "Radio"
            title = current_track.get("title", "Stream") if current_track else "Stream"

            # Write restart command to control file
            command = {
                "action": "restart",
                "artist": artist,
                "title": title,
                "timestamp": datetime.utcnow().isoformat(),
            }

            with open(self.control_file, "w") as f:
                json.dump(command, f)

            logger.info(f"Sent restart command: {artist} - {title}")

            # Wait for restart to complete (stream stops then starts)
            await asyncio.sleep(2.0)

            # Wait up to 10 seconds for stream to restart
            for i in range(20):
                await asyncio.sleep(0.5)
                status = self.get_status()
                if status.get("running"):
                    logger.info("Stream restarted successfully")
                    return {
                        "success": True,
                        "message": "Stream restarted successfully",
                        "status": status,
                    }

            # Timeout
            logger.warning("Stream restart timeout")
            return {"success": False, "message": "Stream restart timeout - check stream logs"}

        except Exception as e:
            logger.error(f"Failed to restart stream: {e}", exc_info=True)
            return {"success": False, "message": f"Failed to restart stream: {str(e)}"}

    async def switch_track(self, artist: str, title: str, loop_path: Optional[Path] = None) -> dict:
        """Switch to a different track.

        Note: Track switching is handled by the metadata watcher service
        via AzuraCast webhooks. This method is provided for compatibility
        but actual track switching should be done through the metadata watcher.

        Args:
            artist: Artist name.
            title: Track title.
            loop_path: Optional custom loop path.

        Returns:
            dict: Switch result.
        """
        logger.info(f"Track switch requested: {artist} - {title}")

        # Track switching is handled by the metadata watcher service
        # The dashboard doesn't directly control track switches
        return {
            "success": False,
            "message": "Track switching is controlled by AzuraCast webhooks, not the dashboard",
        }
