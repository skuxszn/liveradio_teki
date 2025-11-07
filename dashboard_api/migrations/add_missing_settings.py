"""Add any missing .env variables to dashboard settings.

This migration ensures all required settings exist in the dashboard database.
Run this after deploying the dynamic configuration system.
"""

import os
import sys

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from models.config import Setting
from database import SessionLocal

# Define all settings that should be in dashboard
REQUIRED_SETTINGS = {
    "stream": [
        ("YOUTUBE_STREAM_KEY", "", True, "YouTube live stream key"),
        ("AZURACAST_URL", "http://localhost", False, "AzuraCast server URL"),
        ("AZURACAST_API_KEY", "", True, "AzuraCast API key"),
        ("AZURACAST_AUDIO_URL", "", False, "AzuraCast audio stream URL"),
        ("RTMP_ENDPOINT", "rtmp://nginx-rtmp:1935/live/stream", False, "Internal RTMP endpoint"),
        ("WEBHOOK_SECRET", "", True, "AzuraCast webhook secret"),
    ],
    "encoding": [
        ("VIDEO_RESOLUTION", "1280:720", False, "Video resolution (width:height)"),
        ("VIDEO_BITRATE", "3000k", False, "Video bitrate"),
        ("AUDIO_BITRATE", "192k", False, "Audio bitrate"),
        ("VIDEO_ENCODER", "libx264", False, "FFmpeg video encoder"),
        ("FFMPEG_PRESET", "veryfast", False, "FFmpeg encoding preset"),
        ("FADE_DURATION", "1.0", False, "Audio/video fade duration (seconds)"),
        ("TRACK_OVERLAP_DURATION", "2.0", False, "Track transition overlap (seconds)"),
        ("FFMPEG_LOG_LEVEL", "info", False, "FFmpeg log verbosity"),
        ("MAX_RESTART_ATTEMPTS", "3", False, "Max FFmpeg restart attempts"),
        ("RESTART_COOLDOWN_SECONDS", "60", False, "Cooldown between restarts"),
    ],
    "paths": [
        ("LOOPS_PATH", "/srv/loops", False, "Video loops directory"),
        ("DEFAULT_LOOP", "/srv/loops/default.mp4", False, "Default loop video file"),
        ("LOG_PATH", "/var/log/radio", False, "Log files directory"),
    ],
    "security": [
        ("JWT_SECRET", "", True, "JWT signing secret"),
        ("API_TOKEN", "", True, "Internal API token for service communication"),
    ],
    "advanced": [
        ("LOG_LEVEL", "INFO", False, "Application log level"),
        ("DEBUG", "false", False, "Enable debug mode"),
        ("ENVIRONMENT", "production", False, "Environment name"),
        ("ENABLE_METRICS", "true", False, "Enable Prometheus metrics"),
        ("CONFIG_REFRESH_INTERVAL", "60", False, "Config refresh interval (seconds)"),
    ],
    "database": [
        ("POSTGRES_HOST", "postgres", False, "PostgreSQL hostname"),
        ("POSTGRES_PORT", "5432", False, "PostgreSQL port"),
        ("POSTGRES_USER", "radio", False, "PostgreSQL username"),
        ("POSTGRES_PASSWORD", "", True, "PostgreSQL password"),
        ("POSTGRES_DB", "radio_db", False, "PostgreSQL database name"),
    ],
    "notifications": [
        ("DISCORD_WEBHOOK_URL", "", False, "Discord webhook for notifications"),
        ("SLACK_WEBHOOK_URL", "", False, "Slack webhook for notifications"),
    ],
}


def migrate_settings(db: Session):
    """Add missing settings to database."""
    added_count = 0
    updated_count = 0

    for category, settings in REQUIRED_SETTINGS.items():
        for key, default_value, is_secret, description in settings:
            # Check if setting exists
            existing = (
                db.query(Setting).filter(Setting.category == category, Setting.key == key).first()
            )

            if not existing:
                # Try to get value from environment
                env_value = os.getenv(key, default_value)

                # Create setting
                setting = Setting(
                    category=category,
                    key=key,
                    value=env_value if env_value != default_value else None,
                    value_type="string",  # Default to string type
                    default_value=default_value,
                    description=description,
                    is_secret=is_secret,
                )
                db.add(setting)
                added_count += 1
                print(f"Added: {category}.{key} = {env_value if not is_secret else '***'}")
            else:
                # Update description and default if they're missing or different
                changed = False
                if not existing.description or existing.description != description:
                    existing.description = description
                    changed = True
                if existing.default_value != default_value:
                    existing.default_value = default_value
                    changed = True
                if existing.is_secret != is_secret:
                    existing.is_secret = is_secret
                    changed = True

                if changed:
                    updated_count += 1
                    print(f"Updated: {category}.{key}")

    db.commit()
    print(f"\nMigration complete:")
    print(f"  - {added_count} settings added")
    print(f"  - {updated_count} settings updated")


if __name__ == "__main__":
    print("=" * 60)
    print("Dashboard Settings Migration")
    print("=" * 60)
    print()

    db = SessionLocal()
    try:
        migrate_settings(db)
        print("\n✅ Migration successful!")
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()
