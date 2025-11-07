"""FastAPI application for metadata watcher service.

Provides webhook endpoints for AzuraCast track changes and health monitoring.
"""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

import aiohttp
from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel, Field

from config import Config
from config_fetcher import ConfigFetcher
from ffmpeg_manager import FFmpegManager
from track_resolver import TrackResolver

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# Global instances (initialized in lifespan)
config: Optional[Config] = None
config_fetcher: Optional[ConfigFetcher] = None
ffmpeg_manager: Optional[FFmpegManager] = None
track_resolver: Optional[TrackResolver] = None


# Pydantic models for request/response validation
class SongInfo(BaseModel):
    """Song information from AzuraCast webhook."""

    id: str = Field(..., description="AzuraCast song ID")
    artist: str = Field(..., description="Artist name")
    title: str = Field(..., description="Song title")
    album: Optional[str] = Field("", description="Album name")
    duration: Optional[int] = Field(None, description="Duration in seconds")


class StationInfo(BaseModel):
    """Station information from AzuraCast webhook."""

    id: int = Field(..., description="Station ID")  # AzuraCast sends as integer
    name: str = Field(..., description="Station name")


class NowPlayingInfo(BaseModel):
    """Now playing information from AzuraCast."""

    song: SongInfo
    duration: Optional[int] = None
    playlist: Optional[str] = None
    streamer: Optional[str] = None
    is_request: Optional[bool] = False


class WebhookPayload(BaseModel):
    """AzuraCast webhook payload structure (actual format)."""

    now_playing: NowPlayingInfo
    station: StationInfo


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
    timestamp: str
    azuracast_reachable: bool
    ffmpeg_status: str


class StatusResponse(BaseModel):
    """Status endpoint response."""

    service: str
    status: str
    timestamp: str
    current_track: Optional[dict]
    ffmpeg_process: Optional[dict]


class ManualSwitchRequest(BaseModel):
    """Manual track switch request."""

    artist: str = Field(..., description="Artist name")
    title: str = Field(..., description="Song title")
    song_id: Optional[str] = Field(None, description="Optional song ID")


async def background_task_loop():
    """Background task to check control commands and update status."""
    logger.info("Starting background task loop...")

    while True:
        try:
            # Check for control commands from dashboard
            if ffmpeg_manager:
                await ffmpeg_manager.check_control_commands()
                # Update status file periodically
                ffmpeg_manager.update_status_file()

                # Check if FFmpeg process died unexpectedly
                if ffmpeg_manager.current_process:
                    if not ffmpeg_manager.current_process.is_running:
                        # Process died - read logs
                        if ffmpeg_manager.current_process.log_file:
                            try:
                                with open(ffmpeg_manager.current_process.log_file, "r") as f:
                                    error_lines = f.readlines()[-20:]  # Last 20 lines
                                    error_msg = "".join(error_lines)

                                logger.error(f"FFmpeg process died unexpectedly:\n{error_msg}")
                                ffmpeg_manager.last_error = (
                                    f"Process crashed: {error_msg[-300:]}"
                                    if len(error_msg) > 300
                                    else f"Process crashed: {error_msg}"
                                )
                                ffmpeg_manager.current_process = None
                                ffmpeg_manager.update_status_file()
                            except Exception as e:
                                logger.error(f"Error reading crash log: {e}")

            # Sleep for 1 second before next check
            await asyncio.sleep(1.0)

        except asyncio.CancelledError:
            logger.info("Background task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in background task: {e}", exc_info=True)
            await asyncio.sleep(1.0)


async def on_config_change(new_config: Config, changed_keys: list):
    """Handle configuration changes.

    Args:
        new_config: New configuration object.
        changed_keys: List of keys that changed.
    """
    global config

    logger.info(f"Configuration updated: {', '.join(changed_keys)}")

    # Update global config
    config = new_config

    # UPDATE ffmpeg_manager config so it uses new settings!
    if ffmpeg_manager:
        ffmpeg_manager.config = new_config
        logger.info("FFmpeg manager config updated with new settings")

    # Update track_resolver config
    if track_resolver:
        track_resolver.config = new_config
        logger.info("Track resolver config updated with new settings")

    # Critical changes that require restart (RTMP, video settings, etc.)
    critical_keys = {
        "azuracast_audio_url",
        "rtmp_endpoint",
        "video_resolution",
        "video_bitrate",
        "audio_bitrate",
        "video_encoder",
        "ffmpeg_preset",
    }

    if any(key in critical_keys for key in changed_keys):
        logger.warning("Critical configuration changed - stream restart may be required")
        if ffmpeg_manager:
            ffmpeg_manager.last_error = (
                f"Configuration updated: {', '.join(changed_keys)}. Please restart stream."
            )
            ffmpeg_manager.update_status_file()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown."""
    global config, config_fetcher, ffmpeg_manager, track_resolver

    # Startup
    logger.info("Starting metadata watcher service...")
    background_task = None
    config_refresh_task = None

    try:
        # Load initial configuration from env (fallback)
        import os

        config = Config.from_env()
        config.validate()
        logger.info(f"Initial configuration loaded from environment: {config.environment}")

        # Initialize config fetcher for dynamic updates
        dashboard_url = os.getenv("DASHBOARD_API_URL", "http://dashboard-api:9001")
        api_token = os.getenv("API_TOKEN", "")

        if dashboard_url and api_token:
            logger.info(f"Initializing dynamic config fetcher: {dashboard_url}")
            config_fetcher = ConfigFetcher(
                dashboard_url=dashboard_url,
                api_token=api_token,
                refresh_interval=int(os.getenv("CONFIG_REFRESH_INTERVAL", "60")),
            )

            # Try to fetch initial config from dashboard
            dashboard_config = await config_fetcher.fetch_config()
            if dashboard_config:
                config = dashboard_config
                logger.info("Using configuration from dashboard database")
            else:
                logger.warning("Failed to fetch config from dashboard, using environment variables")

            # Start auto-refresh in background
            config_refresh_task = asyncio.create_task(
                config_fetcher.start_auto_refresh(callback=on_config_change)
            )
        else:
            logger.warning(
                "No DASHBOARD_API_URL or API_TOKEN - using static config from environment"
            )

        # Initialize components
        track_resolver = TrackResolver(config)
        ffmpeg_manager = FFmpegManager(config)

        # Start background task for control commands and status updates
        background_task = asyncio.create_task(background_task_loop())

        logger.info("Service started successfully")
        yield

    except Exception as e:
        logger.error(f"Failed to start service: {e}", exc_info=True)
        raise

    finally:
        # Shutdown
        logger.info("Shutting down metadata watcher service...")

        # Cancel background tasks
        if background_task:
            background_task.cancel()
            try:
                await background_task
            except asyncio.CancelledError:
                pass

        if config_refresh_task:
            config_refresh_task.cancel()
            try:
                await config_refresh_task
            except asyncio.CancelledError:
                pass

        if ffmpeg_manager:
            await ffmpeg_manager.cleanup()
        logger.info("Service shut down complete")


# Create FastAPI app
app = FastAPI(
    title="Metadata Watcher Service",
    description="Webhook receiver for AzuraCast track changes with FFmpeg orchestration",
    version="1.0.0",
    lifespan=lifespan,
)


@app.post("/webhook/azuracast", status_code=status.HTTP_200_OK)
async def azuracast_webhook(request: Request):
    """Handle AzuraCast track change webhook.

    Args:
        request: FastAPI request object for header access and body.

    Returns:
        dict: Acknowledgment response.

    Raises:
        HTTPException: If webhook secret validation fails or processing errors.
    """
    # Log raw payload for debugging
    try:
        raw_body = await request.json()
        logger.info(f"Raw webhook payload: {raw_body}")
    except Exception as e:
        logger.error(f"Failed to parse webhook body: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid JSON payload: {str(e)}",
        )

    # Validate payload structure
    try:
        payload = WebhookPayload(**raw_body)
    except Exception as e:
        logger.error(f"Payload validation failed: {e}")
        logger.error(f"Received payload: {raw_body}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid payload structure: {str(e)}",
        )

    # Validate webhook secret if configured
    if config.webhook_secret:
        # Check X-Webhook-Secret header first
        provided_secret = request.headers.get("X-Webhook-Secret")

        # If not found, check HTTP Basic Auth (AzuraCast uses this)
        if not provided_secret:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Basic "):
                # Decode Basic Auth
                import base64

                try:
                    auth_decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
                    # Format is "username:password"
                    if ":" in auth_decoded:
                        username, password = auth_decoded.split(":", 1)
                        # Accept if password matches webhook secret (username is typically "azuracast")
                        if password == config.webhook_secret:
                            provided_secret = password
                except Exception as e:
                    logger.warning(f"Failed to decode Basic Auth: {e}")

        # Validate secret
        if not provided_secret or provided_secret != config.webhook_secret:
            logger.warning(f"Invalid webhook authentication from {request.client.host}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook secret"
            )

    # Extract song info from now_playing
    song = payload.now_playing.song

    logger.info(f"Received webhook: {song.artist} - {song.title} " f"(ID: {song.id})")

    try:
        # Resolve track to video loop
        loop_path = track_resolver.resolve_loop(
            artist=song.artist,
            title=song.title,
            song_id=song.id,
            album=song.album or "",
        )

        # Switch FFmpeg process to new track
        track_key = track_resolver._normalize_track_key(song.artist, song.title)

        success = await ffmpeg_manager.switch_track(
            track_key=track_key,
            artist=song.artist,
            title=song.title,
            loop_path=loop_path,
        )

        if not success:
            logger.error(f"Failed to switch to track: {track_key}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to switch track"
            )

        return {
            "status": "success",
            "message": "Track switched successfully",
            "track": {
                "artist": song.artist,
                "title": song.title,
                "loop": str(loop_path),
            },
        }

    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal error: {str(e)}"
        )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint.

    Checks:
    - Service is running
    - AzuraCast is reachable
    - FFmpeg process status

    Returns:
        HealthResponse: Health status information.
    """
    azuracast_reachable = False

    # Check AzuraCast connectivity
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{config.azuracast_url}/api/status",
                headers={"X-API-Key": config.azuracast_api_key},
                timeout=aiohttp.ClientTimeout(total=5),
            ) as response:
                azuracast_reachable = response.status == 200
    except Exception as e:
        logger.warning(f"AzuraCast health check failed: {e}")

    # Get FFmpeg status
    ffmpeg_status = ffmpeg_manager.get_status()

    return HealthResponse(
        status="healthy" if azuracast_reachable else "degraded",
        service="metadata-watcher",
        timestamp=datetime.now().isoformat(),
        azuracast_reachable=azuracast_reachable,
        ffmpeg_status=ffmpeg_status["status"],
    )


@app.get("/status", response_model=StatusResponse)
async def get_status():
    """Get detailed service status.

    Returns:
        StatusResponse: Detailed status information.
    """
    ffmpeg_status = ffmpeg_manager.get_status()

    current_track = None
    if ffmpeg_status["process"]:
        current_track = {
            "track_key": ffmpeg_status["process"]["track_key"],
            "uptime_seconds": ffmpeg_status["process"]["uptime_seconds"],
            "started_at": ffmpeg_status["process"]["started_at"],
        }

    return StatusResponse(
        service="metadata-watcher",
        status=ffmpeg_status["status"],
        timestamp=datetime.now().isoformat(),
        current_track=current_track,
        ffmpeg_process=ffmpeg_status["process"],
    )


@app.post("/manual/switch", status_code=status.HTTP_200_OK)
async def manual_track_switch(payload: ManualSwitchRequest, request: Request):
    """Manual track switch endpoint for testing.

    Requires API token authentication.

    Args:
        payload: Track information for manual switch.
        request: FastAPI request object for header access.

    Returns:
        dict: Switch result.

    Raises:
        HTTPException: If authentication fails or switch errors.
    """
    # Validate API token if configured
    if config.api_token:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid authorization header",
            )

        provided_token = auth_header.split(" ")[1]
        if provided_token != config.api_token:
            logger.warning(f"Invalid API token from {request.client.host}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API token"
            )

    logger.info(f"Manual switch requested: {payload.artist} - {payload.title}")

    try:
        # Resolve loop
        loop_path = track_resolver.resolve_loop(
            artist=payload.artist,
            title=payload.title,
            song_id=payload.song_id,
        )

        # Switch track
        track_key = track_resolver._normalize_track_key(payload.artist, payload.title)
        success = await ffmpeg_manager.switch_track(
            track_key=track_key,
            artist=payload.artist,
            title=payload.title,
            loop_path=loop_path,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to switch track"
            )

        return {
            "status": "success",
            "message": "Manual track switch successful",
            "track": {
                "artist": payload.artist,
                "title": payload.title,
                "loop": str(loop_path),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Manual switch error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal error: {str(e)}"
        )


@app.get("/logs/latest")
async def get_latest_logs(request: Request):
    """Get latest FFmpeg log file content.

    Returns:
        dict: Log file information and content.

    Raises:
        HTTPException: If authentication fails.
    """
    # Validate API token
    if config.api_token:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Unauthorized")

        provided_token = auth_header.split(" ")[1]
        if provided_token != config.api_token:
            raise HTTPException(status_code=401, detail="Invalid token")

    try:
        # Find latest log file
        from pathlib import Path

        log_dir = Path("/var/log/radio")

        if not log_dir.exists():
            return {"logs": "Log directory does not exist", "timestamp": None}

        log_files = sorted(
            log_dir.glob("ffmpeg_*.log"), key=lambda x: x.stat().st_mtime, reverse=True
        )

        if not log_files:
            return {"logs": "No log files found", "timestamp": None}

        latest_log = log_files[0]

        # Read last 100 lines
        with open(latest_log, "r") as f:
            lines = f.readlines()
            last_lines = lines[-100:]  # Last 100 lines

        return {
            "logs": "".join(last_lines),
            "log_file": str(latest_log.name),
            "timestamp": datetime.fromtimestamp(latest_log.stat().st_mtime).isoformat(),
            "size_bytes": latest_log.stat().st_size,
        }

    except Exception as e:
        logger.error(f"Error reading logs: {e}", exc_info=True)
        return {"error": str(e), "logs": None}


@app.get("/")
async def root():
    """Root endpoint.

    Returns:
        dict: Service information.
    """
    return {
        "service": "metadata-watcher",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "webhook": "/webhook/azuracast",
            "health": "/health",
            "status": "/status",
            "manual_switch": "/manual/switch",
            "logs": "/logs/latest",
        },
    }


if __name__ == "__main__":
    import uvicorn

    # Load config for port
    config = Config.from_env()

    uvicorn.run(
        "metadata_watcher.app:app",
        host="0.0.0.0",
        port=config.watcher_port,
        log_level=config.log_level.lower(),
        reload=config.debug,
    )
