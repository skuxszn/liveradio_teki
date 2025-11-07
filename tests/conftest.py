"""
Pytest configuration and shared fixtures for all tests
"""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock
import tempfile
import shutil

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(project_root))


@pytest.fixture(scope="session")
def project_root_path():
    """Return the project root directory path."""
    return os.path.dirname(os.path.abspath(__file__))


@pytest.fixture(scope="session")
def test_env_vars():
    """Provide test environment variables."""
    return {
        "YOUTUBE_STREAM_KEY": "test-stream-key",
        "POSTGRES_USER": "test_radio",
        "POSTGRES_PASSWORD": "test_password",
        "POSTGRES_DB": "test_radio_db",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "AZURACAST_URL": "http://test.azuracast.local",
        "AZURACAST_API_KEY": "test-api-key",
        "RTMP_ENDPOINT": "rtmp://localhost:1935/live/stream",
        "AUDIO_URL": "http://test.azuracast.local:8000/radio",
        "LOOPS_DIRECTORY": "/tmp/test_loops",
        "LOG_LEVEL": "DEBUG",
        "WEBHOOK_SECRET": "test-webhook-secret",
        "API_TOKEN": "test-api-token",
        "DISCORD_WEBHOOK_URL": "",
        "SLACK_WEBHOOK_URL": "",
        "ENVIRONMENT": "test",
    }


@pytest.fixture
def mock_env(monkeypatch, test_env_vars):
    """Mock environment variables for testing."""
    for key, value in test_env_vars.items():
        monkeypatch.setenv(key, value)


@pytest.fixture
def temp_loops_dir():
    """Create temporary directory for test video loops."""
    temp_dir = tempfile.mkdtemp(prefix="test_loops_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_webhook_payload():
    """Provide a sample AzuraCast webhook payload."""
    return {
        "song": {
            "id": "123",
            "artist": "Test Artist",
            "title": "Test Song",
            "album": "Test Album",
            "duration": 180,
        },
        "station": {
            "id": "1",
            "name": "Test Station",
        },
    }


@pytest.fixture
def mock_ffmpeg_process():
    """Mock FFmpeg process for testing."""
    process = Mock()
    process.pid = 12345
    process.returncode = None
    process.poll = Mock(return_value=None)
    process.communicate = Mock(return_value=(b"", b""))
    process.terminate = Mock()
    process.kill = Mock()
    process.wait = Mock()
    return process


@pytest.fixture
def mock_database_connection():
    """Mock database connection for testing."""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    cursor.fetchone.return_value = None
    cursor.fetchall.return_value = []
    return conn


@pytest.fixture
def mock_requests_session(monkeypatch):
    """Mock requests session for testing."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok"}
    mock_response.text = "OK"

    mock_session = Mock()
    mock_session.get.return_value = mock_response
    mock_session.post.return_value = mock_response

    import requests

    monkeypatch.setattr(requests, "get", mock_session.get)
    monkeypatch.setattr(requests, "post", mock_session.post)

    return mock_session
