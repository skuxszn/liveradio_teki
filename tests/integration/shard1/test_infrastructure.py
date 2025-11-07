"""
Integration tests for SHARD-1: Core Infrastructure Setup

Tests verify that all Docker services start correctly and can communicate
with each other.
"""

import os
import subprocess
import time
from typing import Generator

import pytest
import requests


@pytest.fixture(scope="module")
def docker_services() -> Generator[None, None, None]:
    """
    Start Docker Compose services for testing.
    
    Yields control to tests after services are up, then tears them down.
    """
    # Start services
    subprocess.run(
        ["docker-compose", "up", "-d"],
        check=True,
        cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    )
    
    # Wait for services to be ready
    time.sleep(10)
    
    yield
    
    # Cleanup
    subprocess.run(
        ["docker-compose", "down"],
        check=False,
        cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    )


class TestNginxRTMP:
    """Tests for nginx-rtmp service."""
    
    def test_nginx_rtmp_health_endpoint(self, docker_services: None) -> None:
        """Test that nginx-rtmp health endpoint returns 200 OK."""
        response = requests.get("http://localhost:8080/health", timeout=5)
        assert response.status_code == 200
        assert response.text.strip() == "OK"
    
    def test_nginx_rtmp_stats_endpoint(self, docker_services: None) -> None:
        """Test that nginx-rtmp stats endpoint is accessible."""
        response = requests.get("http://localhost:8080/stat", timeout=5)
        assert response.status_code == 200
        # Should return XML statistics
        assert "rtmp" in response.text.lower()
    
    def test_nginx_rtmp_accepts_connections(self, docker_services: None) -> None:
        """Test that nginx-rtmp accepts connections on port 1935."""
        import socket
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        try:
            result = sock.connect_ex(("localhost", 1935))
            assert result == 0, "RTMP port 1935 should be open"
        finally:
            sock.close()


class TestPrometheus:
    """Tests for Prometheus service."""
    
    def test_prometheus_health_endpoint(self, docker_services: None) -> None:
        """Test that Prometheus health endpoint returns 200 OK."""
        response = requests.get("http://localhost:9090/-/healthy", timeout=5)
        assert response.status_code == 200
    
    def test_prometheus_metrics_endpoint(self, docker_services: None) -> None:
        """Test that Prometheus metrics endpoint is accessible."""
        response = requests.get("http://localhost:9090/metrics", timeout=5)
        assert response.status_code == 200
        assert "prometheus_" in response.text
    
    def test_prometheus_config_loaded(self, docker_services: None) -> None:
        """Test that Prometheus loaded its configuration."""
        response = requests.get("http://localhost:9090/api/v1/status/config", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


class TestPostgres:
    """Tests for PostgreSQL service."""
    
    def test_postgres_accepts_connections(self, docker_services: None) -> None:
        """Test that PostgreSQL accepts connections on port 5432."""
        import socket
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        try:
            result = sock.connect_ex(("localhost", 5432))
            assert result == 0, "PostgreSQL port 5432 should be open"
        finally:
            sock.close()
    
    def test_postgres_health_check(self, docker_services: None) -> None:
        """Test PostgreSQL health using docker exec."""
        result = subprocess.run(
            [
                "docker",
                "exec",
                "radio_postgres",
                "pg_isready",
                "-U",
                "radio",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "accepting connections" in result.stdout


class TestServiceCommunication:
    """Tests for inter-service communication."""
    
    def test_services_on_same_network(self, docker_services: None) -> None:
        """Test that all services are on the same Docker network."""
        result = subprocess.run(
            ["docker", "network", "inspect", "liveradio_teki_radio_network"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        
        # Check that key services are on the network
        network_data = result.stdout
        assert "radio_nginx_rtmp" in network_data
        assert "radio_prometheus" in network_data
        assert "radio_postgres" in network_data
    
    def test_nginx_rtmp_resolvable_from_network(self, docker_services: None) -> None:
        """Test that nginx-rtmp hostname is resolvable within network."""
        result = subprocess.run(
            [
                "docker",
                "exec",
                "radio_postgres",
                "ping",
                "-c",
                "1",
                "nginx-rtmp",
            ],
            capture_output=True,
        )
        assert result.returncode == 0


class TestHealthChecks:
    """Tests for Docker health checks."""
    
    def test_all_services_healthy(self, docker_services: None) -> None:
        """Test that all services report as healthy."""
        # Give services time to become healthy
        time.sleep(30)
        
        result = subprocess.run(
            ["docker-compose", "ps"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        )
        
        # All services should be up and healthy (or starting)
        assert "radio_nginx_rtmp" in result.stdout
        assert "radio_prometheus" in result.stdout
        assert "radio_postgres" in result.stdout


class TestEnvironmentVariables:
    """Tests for environment variable configuration."""
    
    def test_env_example_exists(self) -> None:
        """Test that env.example file exists."""
        env_example_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "env.example",
        )
        assert os.path.exists(env_example_path)
    
    def test_env_example_has_required_vars(self) -> None:
        """Test that env.example contains required variables."""
        env_example_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "env.example",
        )
        
        with open(env_example_path, "r") as f:
            content = f.read()
        
        required_vars = [
            "YOUTUBE_STREAM_KEY",
            "POSTGRES_PASSWORD",
            "AZURACAST_URL",
            "RTMP_ENDPOINT",
        ]
        
        for var in required_vars:
            assert var in content, f"Required variable {var} not in env.example"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])




