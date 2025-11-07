"""
Sample data and fixtures for testing
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List


FIXTURES_DIR = Path(__file__).parent


def load_json_fixture(filename: str) -> Dict[str, Any]:
    """Load a JSON fixture file."""
    filepath = FIXTURES_DIR / "payloads" / filename
    with open(filepath, "r") as f:
        return json.load(f)


def get_azuracast_webhook_payload() -> Dict[str, Any]:
    """Get a standard AzuraCast webhook payload."""
    return load_json_fixture("azuracast_webhook.json")


def get_minimal_webhook_payload() -> Dict[str, Any]:
    """Get a minimal AzuraCast webhook payload."""
    return load_json_fixture("azuracast_webhook_minimal.json")


def get_sample_track_metadata() -> List[Dict[str, Any]]:
    """Get sample track metadata for testing."""
    return [
        {
            "track_key": "artist name - song title",
            "artist": "Artist Name",
            "title": "Song Title",
            "album": "Album Name",
            "azuracast_song_id": "123",
            "loop_file_path": "/srv/loops/tracks/track_123_loop.mp4",
            "duration": 180,
        },
        {
            "track_key": "test artist - test song",
            "artist": "Test Artist",
            "title": "Test Song",
            "album": "Test Album",
            "azuracast_song_id": "456",
            "loop_file_path": "/srv/loops/tracks/track_456_loop.mp4",
            "duration": 200,
        },
        {
            "track_key": "dj mix - epic beats",
            "artist": "DJ Mix",
            "title": "Epic Beats",
            "album": "Best of 2025",
            "azuracast_song_id": "789",
            "loop_file_path": "/srv/loops/tracks/track_789_loop.mp4",
            "duration": 240,
        },
    ]


def get_sample_error_events() -> List[Dict[str, Any]]:
    """Get sample error events for testing."""
    return [
        {
            "service": "ffmpeg",
            "severity": "error",
            "message": "FFmpeg process crashed",
            "context": {"pid": 12345, "exit_code": 1, "stderr": "Error opening file"},
        },
        {
            "service": "metadata_watcher",
            "severity": "warning",
            "message": "Audio stream unavailable",
            "context": {"url": "http://azuracast:8000/radio", "retry_count": 2},
        },
        {
            "service": "rtmp",
            "severity": "critical",
            "message": "RTMP connection refused",
            "context": {
                "endpoint": "rtmp://nginx-rtmp:1935/live/stream",
                "error": "Connection timeout",
            },
        },
    ]


def get_sample_ffmpeg_command() -> List[str]:
    """Get a sample FFmpeg command for testing."""
    return [
        "ffmpeg",
        "-re",
        "-stream_loop",
        "-1",
        "-i",
        "/srv/loops/tracks/track_123_loop.mp4",
        "-i",
        "http://azuracast:8000/radio",
        "-map",
        "0:v",
        "-map",
        "1:a",
        "-vf",
        "fade=t=in:st=0:d=1.0,scale=1280:720,format=yuv420p",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-g",
        "50",
        "-keyint_min",
        "50",
        "-b:v",
        "3000k",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-ar",
        "44100",
        "-f",
        "flv",
        "rtmp://nginx-rtmp:1935/live/stream",
    ]


def get_sample_env_vars() -> Dict[str, str]:
    """Get sample environment variables for testing."""
    return {
        "YOUTUBE_STREAM_KEY": "test-stream-key-12345",
        "POSTGRES_USER": "test_radio",
        "POSTGRES_PASSWORD": "test_password",
        "POSTGRES_DB": "test_radio_db",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "AZURACAST_URL": "http://test.azuracast.local",
        "AZURACAST_API_KEY": "test-api-key-67890",
        "RTMP_ENDPOINT": "rtmp://localhost:1935/live/stream",
        "AUDIO_URL": "http://test.azuracast.local:8000/radio",
        "LOOPS_DIRECTORY": "/tmp/test_loops",
        "LOG_LEVEL": "DEBUG",
        "WEBHOOK_SECRET": "test-webhook-secret",
        "API_TOKEN": "test-api-token-abcdef",
        "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/test",
        "SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/test",
        "ENVIRONMENT": "test",
    }


def get_prometheus_metrics_sample() -> str:
    """Get sample Prometheus metrics output."""
    return """# HELP radio_tracks_played_total Total number of tracks played
# TYPE radio_tracks_played_total counter
radio_tracks_played_total 142

# HELP radio_ffmpeg_restarts_total Total number of FFmpeg restarts
# TYPE radio_ffmpeg_restarts_total counter
radio_ffmpeg_restarts_total 3

# HELP radio_errors_total Total number of errors
# TYPE radio_errors_total counter
radio_errors_total{severity="error"} 5
radio_errors_total{severity="critical"} 1

# HELP radio_ffmpeg_status FFmpeg process status
# TYPE radio_ffmpeg_status gauge
radio_ffmpeg_status{status="running"} 1

# HELP radio_stream_uptime_seconds Stream uptime in seconds
# TYPE radio_stream_uptime_seconds gauge
radio_stream_uptime_seconds 86400

# HELP radio_current_track_duration_seconds Current track duration
# TYPE radio_current_track_duration_seconds gauge
radio_current_track_duration_seconds 180
"""
