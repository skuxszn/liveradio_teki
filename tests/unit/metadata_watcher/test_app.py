"""Unit tests for FastAPI application."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    config = Mock()
    config.azuracast_url = "http://test.example.com"
    config.azuracast_api_key = "test-key"
    config.webhook_secret = "test-secret"
    config.api_token = "test-token"
    config.watcher_port = 9000
    config.log_level = "INFO"
    config.debug = False
    config.environment = "testing"
    return config


@pytest.fixture
def mock_ffmpeg_manager():
    """Create a mock FFmpeg manager."""
    manager = Mock()
    manager.switch_track = AsyncMock(return_value=True)
    manager.get_status = Mock(return_value={
        "status": "running",
        "process": {
            "pid": 12345,
            "track_key": "test - track",
            "loop_path": "/test/loop.mp4",
            "uptime_seconds": 100.0,
            "started_at": "2025-11-03T12:00:00"
        }
    })
    manager.cleanup = AsyncMock()
    return manager


@pytest.fixture
def mock_track_resolver():
    """Create a mock track resolver."""
    resolver = Mock()
    resolver.resolve_loop = Mock(return_value=Path("/test/loop.mp4"))
    resolver._normalize_track_key = Mock(return_value="artist - title")
    return resolver


@pytest.fixture
def client(mock_config, mock_ffmpeg_manager, mock_track_resolver):
    """Create a test client with mocked dependencies."""
    with patch('metadata_watcher.app.Config') as MockConfig, \
         patch('metadata_watcher.app.FFmpegManager') as MockFFmpegManager, \
         patch('metadata_watcher.app.TrackResolver') as MockTrackResolver:

        MockConfig.from_env.return_value = mock_config
        MockFFmpegManager.return_value = mock_ffmpeg_manager
        MockTrackResolver.return_value = mock_track_resolver

        # Import app after patching
        from metadata_watcher.app import app
        
        # Set global instances
        import metadata_watcher.app as app_module
        app_module.config = mock_config
        app_module.ffmpeg_manager = mock_ffmpeg_manager
        app_module.track_resolver = mock_track_resolver

        with TestClient(app) as test_client:
            yield test_client


class TestRootEndpoint:
    """Test root endpoint."""

    def test_root(self, client):
        """Test root endpoint returns service info."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "metadata-watcher"
        assert data["version"] == "1.0.0"
        assert "endpoints" in data


class TestWebhookEndpoint:
    """Test AzuraCast webhook endpoint."""

    def test_webhook_valid_payload(self, client):
        """Test webhook with valid payload."""
        payload = {
            "song": {
                "id": "123",
                "artist": "Test Artist",
                "title": "Test Title",
                "album": "Test Album",
                "duration": 180
            },
            "station": {
                "id": "1",
                "name": "Test Station"
            }
        }

        response = client.post(
            "/webhook/azuracast",
            json=payload,
            headers={"X-Webhook-Secret": "test-secret"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "track" in data

    def test_webhook_invalid_secret(self, client):
        """Test webhook with invalid secret."""
        payload = {
            "song": {
                "id": "123",
                "artist": "Test Artist",
                "title": "Test Title"
            },
            "station": {
                "id": "1",
                "name": "Test Station"
            }
        }

        response = client.post(
            "/webhook/azuracast",
            json=payload,
            headers={"X-Webhook-Secret": "wrong-secret"}
        )

        assert response.status_code == 401

    def test_webhook_missing_secret(self, client):
        """Test webhook without secret header."""
        payload = {
            "song": {
                "id": "123",
                "artist": "Test Artist",
                "title": "Test Title"
            },
            "station": {
                "id": "1",
                "name": "Test Station"
            }
        }

        response = client.post("/webhook/azuracast", json=payload)

        assert response.status_code == 401

    def test_webhook_invalid_payload(self, client):
        """Test webhook with invalid payload structure."""
        payload = {
            "invalid": "data"
        }

        response = client.post(
            "/webhook/azuracast",
            json=payload,
            headers={"X-Webhook-Secret": "test-secret"}
        )

        assert response.status_code == 422  # Validation error

    def test_webhook_missing_fields(self, client):
        """Test webhook with missing required fields."""
        payload = {
            "song": {
                "id": "123"
                # Missing artist and title
            },
            "station": {
                "id": "1",
                "name": "Test Station"
            }
        }

        response = client.post(
            "/webhook/azuracast",
            json=payload,
            headers={"X-Webhook-Secret": "test-secret"}
        )

        assert response.status_code == 422


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check_success(self, client):
        """Test health check when everything is healthy."""
        with patch('metadata_watcher.app.aiohttp.ClientSession') as mock_session:
            # Mock successful AzuraCast response
            mock_response = Mock()
            mock_response.status = 200
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock()

            mock_get = Mock()
            mock_get.__aenter__ = AsyncMock(return_value=mock_response)
            mock_get.__aexit__ = AsyncMock()

            mock_session_instance = Mock()
            mock_session_instance.get.return_value = mock_get
            mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session_instance.__aexit__ = AsyncMock()

            mock_session.return_value = mock_session_instance

            response = client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["service"] == "metadata-watcher"
            assert data["azuracast_reachable"] is True
            assert data["ffmpeg_status"] == "running"

    def test_health_check_azuracast_unreachable(self, client):
        """Test health check when AzuraCast is unreachable."""
        with patch('metadata_watcher.app.aiohttp.ClientSession') as mock_session:
            # Mock failed AzuraCast response
            mock_session.side_effect = Exception("Connection failed")

            response = client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"
            assert data["azuracast_reachable"] is False


class TestStatusEndpoint:
    """Test status endpoint."""

    def test_status_with_running_process(self, client):
        """Test status endpoint with running process."""
        response = client.get("/status")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "metadata-watcher"
        assert data["status"] == "running"
        assert data["current_track"] is not None
        assert data["ffmpeg_process"]["pid"] == 12345

    def test_status_no_process(self, client, mock_ffmpeg_manager):
        """Test status endpoint when no process is running."""
        mock_ffmpeg_manager.get_status.return_value = {
            "status": "stopped",
            "process": None
        }

        response = client.get("/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "stopped"
        assert data["current_track"] is None


class TestManualSwitchEndpoint:
    """Test manual track switch endpoint."""

    def test_manual_switch_valid(self, client):
        """Test manual switch with valid token and data."""
        payload = {
            "artist": "Test Artist",
            "title": "Test Title",
            "song_id": "123"
        }

        response = client.post(
            "/manual/switch",
            json=payload,
            headers={"Authorization": "Bearer test-token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_manual_switch_invalid_token(self, client):
        """Test manual switch with invalid token."""
        payload = {
            "artist": "Test Artist",
            "title": "Test Title"
        }

        response = client.post(
            "/manual/switch",
            json=payload,
            headers={"Authorization": "Bearer wrong-token"}
        )

        assert response.status_code == 401

    def test_manual_switch_missing_token(self, client):
        """Test manual switch without authorization header."""
        payload = {
            "artist": "Test Artist",
            "title": "Test Title"
        }

        response = client.post("/manual/switch", json=payload)

        assert response.status_code == 401

    def test_manual_switch_missing_fields(self, client):
        """Test manual switch with missing required fields."""
        payload = {
            "artist": "Test Artist"
            # Missing title
        }

        response = client.post(
            "/manual/switch",
            json=payload,
            headers={"Authorization": "Bearer test-token"}
        )

        assert response.status_code == 422

    def test_manual_switch_ffmpeg_failure(self, client, mock_ffmpeg_manager):
        """Test manual switch when FFmpeg switch fails."""
        mock_ffmpeg_manager.switch_track.return_value = False

        payload = {
            "artist": "Test Artist",
            "title": "Test Title"
        }

        response = client.post(
            "/manual/switch",
            json=payload,
            headers={"Authorization": "Bearer test-token"}
        )

        assert response.status_code == 500




