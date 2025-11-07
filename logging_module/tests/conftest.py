"""Pytest configuration and fixtures for logging_module tests."""

import os
import pytest
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from logging_module.config import LoggingConfig
from logging_module.logger import RadioLogger
from logging_module.analytics import Analytics


@pytest.fixture
def test_config():
    """Create test configuration with in-memory database."""
    config = LoggingConfig(
        postgres_host="localhost",
        postgres_port=5432,
        postgres_user="test",
        postgres_password="test",
        postgres_db="test_radio_db",
        log_level="DEBUG",
        log_path="/tmp/test_radio_logs",
        db_pool_size=1,
        db_max_overflow=0,
        debug=True
    )
    # Override database_url for testing
    config.postgres_host = "sqlite"
    return config


@pytest.fixture
def test_engine(test_config):
    """Create test database engine with in-memory SQLite."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    
    # Create schema
    with open("logging_module/schema.sql", "r") as f:
        schema_sql = f.read()
    
    # Execute schema (skip PostgreSQL-specific parts for SQLite)
    with engine.connect() as conn:
        # Create basic tables for testing
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS play_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                track_key VARCHAR(512) NOT NULL,
                artist VARCHAR(256),
                title VARCHAR(256),
                album VARCHAR(256),
                azuracast_song_id VARCHAR(128),
                loop_file_path VARCHAR(1024),
                started_at TIMESTAMP NOT NULL,
                ended_at TIMESTAMP,
                duration_seconds INTEGER,
                expected_duration_seconds INTEGER,
                ffmpeg_pid INTEGER,
                had_errors BOOLEAN DEFAULT 0,
                error_message TEXT,
                error_count INTEGER DEFAULT 0,
                metadata TEXT
            )
        """))
        
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS error_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                service VARCHAR(64) NOT NULL,
                severity VARCHAR(16) NOT NULL,
                message TEXT NOT NULL,
                context TEXT,
                stack_trace TEXT,
                resolved BOOLEAN DEFAULT 0,
                resolved_at TIMESTAMP,
                play_history_id INTEGER
            )
        """))
        
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                metric_name VARCHAR(128) NOT NULL,
                metric_value NUMERIC NOT NULL,
                unit VARCHAR(32),
                service VARCHAR(64),
                metadata TEXT
            )
        """))
        
        conn.commit()
    
    yield engine
    
    # Cleanup
    engine.dispose()


@pytest.fixture
def test_logger(test_config, test_engine, monkeypatch):
    """Create test RadioLogger instance."""
    # Patch the _create_engine method to use test engine
    def mock_create_engine(self):
        return test_engine
    
    monkeypatch.setattr(RadioLogger, "_create_engine", mock_create_engine)
    
    logger = RadioLogger(test_config)
    yield logger
    logger.close()


@pytest.fixture
def test_analytics(test_config, test_engine, monkeypatch):
    """Create test Analytics instance."""
    # Create analytics with test engine
    analytics = Analytics(test_config)
    analytics.engine = test_engine
    yield analytics
    analytics.close()


@pytest.fixture
def sample_track_info():
    """Sample track information for testing."""
    return {
        "artist": "Test Artist",
        "title": "Test Song",
        "album": "Test Album",
        "azuracast_song_id": "123",
        "duration": 180
    }


@pytest.fixture
def populated_database(test_engine):
    """Populate test database with sample data."""
    with test_engine.connect() as conn:
        # Insert sample play history
        for i in range(10):
            conn.execute(text("""
                INSERT INTO play_history (
                    track_key, artist, title, album, loop_file_path,
                    started_at, ended_at, duration_seconds, ffmpeg_pid,
                    had_errors, error_count
                ) VALUES (
                    :track_key, :artist, :title, :album, :loop_path,
                    datetime('now', '-' || :days || ' days'),
                    datetime('now', '-' || :days || ' days', '+180 seconds'),
                    180, :ffmpeg_pid, :had_errors, 0
                )
            """), {
                "track_key": f"artist {i % 3} - song {i % 5}",
                "artist": f"Artist {i % 3}",
                "title": f"Song {i % 5}",
                "album": f"Album {i % 2}",
                "loop_path": f"/srv/loops/track{i}.mp4",
                "days": i,
                "ffmpeg_pid": 10000 + i,
                "had_errors": 1 if i % 5 == 0 else 0
            })
        
        # Insert sample errors
        for i in range(5):
            conn.execute(text("""
                INSERT INTO error_log (
                    timestamp, service, severity, message, resolved
                ) VALUES (
                    datetime('now', '-' || :days || ' days'),
                    :service, :severity, :message, :resolved
                )
            """), {
                "days": i,
                "service": "ffmpeg" if i % 2 == 0 else "watcher",
                "severity": "error" if i % 2 == 0 else "warning",
                "message": f"Test error {i}",
                "resolved": 1 if i % 3 == 0 else 0
            })
        
        conn.commit()
    
    return test_engine



