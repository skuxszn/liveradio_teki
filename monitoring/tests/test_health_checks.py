"""Tests for health check functionality."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from monitoring.config import MonitoringConfig
from monitoring.health_checks import HealthChecker, HealthStatus


class TestHealthChecker:
    """Test cases for HealthChecker."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return MonitoringConfig(
            azuracast_url="http://test-azuracast:8000",
            azuracast_api_key="test-key",
        )

    @pytest.fixture
    def health_checker(self, config):
        """Create HealthChecker instance."""
        return HealthChecker(config)

    @pytest.mark.asyncio
    async def test_check_liveness(self, health_checker):
        """Test liveness probe."""
        result = await health_checker.check_liveness()

        assert result.status == HealthStatus.HEALTHY
        assert result.message == "Service is alive"
        assert isinstance(result.timestamp, datetime)

    @pytest.mark.asyncio
    async def test_check_readiness_healthy(self, health_checker):
        """Test readiness probe when FFmpeg is running."""
        result = await health_checker.check_readiness(ffmpeg_running=True)

        assert result.status == HealthStatus.HEALTHY
        assert result.message == "Service is ready"
        assert result.details["ffmpeg_running"] is True

    @pytest.mark.asyncio
    async def test_check_readiness_unhealthy(self, health_checker):
        """Test readiness probe when FFmpeg is not running."""
        result = await health_checker.check_readiness(ffmpeg_running=False)

        assert result.status == HealthStatus.UNHEALTHY
        assert "not running" in result.message
        assert result.details["ffmpeg_running"] is False

    @pytest.mark.asyncio
    async def test_check_azuracast_healthy(self, health_checker):
        """Test AzuraCast check when healthy."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await health_checker.check_azuracast()

            assert result.status == HealthStatus.HEALTHY
            assert "reachable" in result.message

    @pytest.mark.asyncio
    async def test_check_azuracast_not_configured(self):
        """Test AzuraCast check when not configured."""
        config = MonitoringConfig(azuracast_url=None)
        checker = HealthChecker(config)

        result = await checker.check_azuracast()

        assert result.status == HealthStatus.DEGRADED
        assert "not configured" in result.message

    @pytest.mark.asyncio
    async def test_check_azuracast_timeout(self, health_checker):
        """Test AzuraCast check timeout."""
        import asyncio

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(side_effect=asyncio.TimeoutError())

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await health_checker.check_azuracast()

            assert result.status == HealthStatus.UNHEALTHY
            assert "timeout" in result.message.lower()

    @pytest.mark.asyncio
    async def test_check_detailed_all_healthy(self, health_checker):
        """Test detailed check when all components healthy."""
        ffmpeg_status = {
            "state": "running",
            "pid": 12345,
            "uptime_seconds": 300,
        }

        with patch.object(
            health_checker, "check_azuracast", new_callable=AsyncMock
        ) as mock_check:
            mock_result = MagicMock()
            mock_result.status = HealthStatus.HEALTHY
            mock_result.message = "AzuraCast reachable"
            mock_check.return_value = mock_result

            result = await health_checker.check_detailed(ffmpeg_status)

            assert result.status == HealthStatus.HEALTHY
            assert "All components healthy" in result.message
            assert "ffmpeg" in result.details["components"]
            assert "azuracast" in result.details["components"]

    @pytest.mark.asyncio
    async def test_check_detailed_degraded(self, health_checker):
        """Test detailed check when degraded."""
        ffmpeg_status = {
            "state": "running",
            "pid": 12345,
            "uptime_seconds": 300,
        }

        with patch.object(
            health_checker, "check_azuracast", new_callable=AsyncMock
        ) as mock_check:
            mock_result = MagicMock()
            mock_result.status = HealthStatus.UNHEALTHY
            mock_result.message = "AzuraCast unreachable"
            mock_check.return_value = mock_result

            result = await health_checker.check_detailed(ffmpeg_status)

            assert result.status == HealthStatus.DEGRADED
            assert "degraded" in result.message.lower()

    @pytest.mark.asyncio
    async def test_check_detailed_unhealthy(self, health_checker):
        """Test detailed check when unhealthy."""
        ffmpeg_status = {
            "state": "stopped",
            "pid": None,
            "uptime_seconds": 0,
        }

        with patch.object(
            health_checker, "check_azuracast", new_callable=AsyncMock
        ) as mock_check:
            mock_result = MagicMock()
            mock_result.status = HealthStatus.UNHEALTHY
            mock_result.message = "AzuraCast unreachable"
            mock_check.return_value = mock_result

            result = await health_checker.check_detailed(ffmpeg_status)

            assert result.status == HealthStatus.UNHEALTHY

    def test_get_health_dict(self, health_checker):
        """Test converting health result to dict."""
        from monitoring.health_checks import HealthCheckResult

        result = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            message="Test message",
            timestamp=datetime.now(),
            details={"test": "data"},
        )

        health_dict = health_checker.get_health_dict(result)

        assert health_dict["status"] == HealthStatus.HEALTHY
        assert health_dict["message"] == "Test message"
        assert "timestamp" in health_dict
        assert health_dict["details"]["test"] == "data"

