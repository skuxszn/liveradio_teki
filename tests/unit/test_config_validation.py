"""
Unit tests for SHARD-1: Configuration validation

Tests validate that infrastructure configuration files are properly formatted
and contain required settings.
"""

import os
import yaml
import pytest
from typing import Any, Dict


def get_project_root() -> str:
    """Get the project root directory."""
    return os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


class TestDockerComposeConfig:
    """Tests for docker-compose.yml configuration."""
    
    def test_docker_compose_file_exists(self) -> None:
        """Test that docker-compose.yml exists."""
        compose_file = os.path.join(get_project_root(), "docker-compose.yml")
        assert os.path.exists(compose_file)
    
    def test_docker_compose_valid_yaml(self) -> None:
        """Test that docker-compose.yml is valid YAML."""
        compose_file = os.path.join(get_project_root(), "docker-compose.yml")
        with open(compose_file, "r") as f:
            data = yaml.safe_load(f)
        assert data is not None
        assert "services" in data
    
    def test_docker_compose_has_required_services(self) -> None:
        """Test that all required services are defined."""
        compose_file = os.path.join(get_project_root(), "docker-compose.yml")
        with open(compose_file, "r") as f:
            data = yaml.safe_load(f)
        
        required_services = ["nginx-rtmp", "metadata-watcher", "postgres", "prometheus"]
        for service in required_services:
            assert service in data["services"], f"Service {service} not found"
    
    def test_services_have_health_checks(self) -> None:
        """Test that critical services have health checks defined."""
        compose_file = os.path.join(get_project_root(), "docker-compose.yml")
        with open(compose_file, "r") as f:
            data = yaml.safe_load(f)
        
        services_requiring_health_checks = ["nginx-rtmp", "postgres", "prometheus"]
        for service in services_requiring_health_checks:
            assert "healthcheck" in data["services"][service], \
                f"Service {service} missing health check"
    
    def test_services_use_custom_network(self) -> None:
        """Test that services use a custom bridge network."""
        compose_file = os.path.join(get_project_root(), "docker-compose.yml")
        with open(compose_file, "r") as f:
            data = yaml.safe_load(f)
        
        assert "networks" in data
        assert "radio_network" in data["networks"]
        
        # Check that services use the network
        for service in data["services"].values():
            assert "networks" in service
            assert "radio_network" in service["networks"]
    
    def test_services_have_restart_policy(self) -> None:
        """Test that services have appropriate restart policies."""
        compose_file = os.path.join(get_project_root(), "docker-compose.yml")
        with open(compose_file, "r") as f:
            data = yaml.safe_load(f)
        
        for service_name, service in data["services"].items():
            assert "restart" in service, \
                f"Service {service_name} missing restart policy"
            assert service["restart"] in ["unless-stopped", "always", "on-failure"]


class TestNginxConfig:
    """Tests for nginx-rtmp configuration."""
    
    def test_nginx_config_exists(self) -> None:
        """Test that nginx.conf exists."""
        config_file = os.path.join(get_project_root(), "nginx-rtmp", "nginx.conf")
        assert os.path.exists(config_file)
    
    def test_nginx_config_has_rtmp_block(self) -> None:
        """Test that nginx.conf contains RTMP configuration."""
        config_file = os.path.join(get_project_root(), "nginx-rtmp", "nginx.conf")
        with open(config_file, "r") as f:
            content = f.read()
        
        assert "rtmp {" in content
        assert "application live {" in content
        assert "live on;" in content
    
    def test_nginx_config_has_http_block(self) -> None:
        """Test that nginx.conf contains HTTP configuration for health checks."""
        config_file = os.path.join(get_project_root(), "nginx-rtmp", "nginx.conf")
        with open(config_file, "r") as f:
            content = f.read()
        
        assert "http {" in content
        assert "location /health" in content
    
    def test_nginx_config_has_youtube_push(self) -> None:
        """Test that nginx.conf is configured to push to YouTube."""
        config_file = os.path.join(get_project_root(), "nginx-rtmp", "nginx.conf")
        with open(config_file, "r") as f:
            content = f.read()
        
        assert "push rtmp://a.rtmp.youtube.com" in content


class TestPrometheusConfig:
    """Tests for Prometheus configuration."""
    
    def test_prometheus_config_exists(self) -> None:
        """Test that prometheus.yml exists."""
        config_file = os.path.join(get_project_root(), "monitoring", "prometheus.yml")
        assert os.path.exists(config_file)
    
    def test_prometheus_config_valid_yaml(self) -> None:
        """Test that prometheus.yml is valid YAML."""
        config_file = os.path.join(get_project_root(), "monitoring", "prometheus.yml")
        with open(config_file, "r") as f:
            data = yaml.safe_load(f)
        assert data is not None
        assert "global" in data
        assert "scrape_configs" in data
    
    def test_prometheus_has_scrape_configs(self) -> None:
        """Test that Prometheus has scrape configurations for services."""
        config_file = os.path.join(get_project_root(), "monitoring", "prometheus.yml")
        with open(config_file, "r") as f:
            data = yaml.safe_load(f)
        
        job_names = [job["job_name"] for job in data["scrape_configs"]]
        expected_jobs = ["prometheus", "metadata-watcher", "nginx-rtmp"]
        
        for job in expected_jobs:
            assert job in job_names, f"Scrape config for {job} not found"
    
    def test_alerting_rules_exist(self) -> None:
        """Test that alerting rules file exists."""
        rules_file = os.path.join(get_project_root(), "monitoring", "alerting_rules.yml")
        assert os.path.exists(rules_file)
    
    def test_alerting_rules_valid_yaml(self) -> None:
        """Test that alerting rules are valid YAML."""
        rules_file = os.path.join(get_project_root(), "monitoring", "alerting_rules.yml")
        with open(rules_file, "r") as f:
            data = yaml.safe_load(f)
        assert data is not None
        assert "groups" in data


class TestEnvironmentConfiguration:
    """Tests for environment configuration."""
    
    def test_env_example_exists(self) -> None:
        """Test that env.example exists."""
        env_file = os.path.join(get_project_root(), "env.example")
        assert os.path.exists(env_file)
    
    def test_env_example_has_critical_variables(self) -> None:
        """Test that env.example contains critical variables."""
        env_file = os.path.join(get_project_root(), "env.example")
        with open(env_file, "r") as f:
            content = f.read()
        
        critical_vars = [
            "YOUTUBE_STREAM_KEY",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "POSTGRES_DB",
            "AZURACAST_URL",
        ]
        
        for var in critical_vars:
            assert var in content, f"Critical variable {var} not in env.example"
    
    def test_env_example_has_comments(self) -> None:
        """Test that env.example has helpful comments."""
        env_file = os.path.join(get_project_root(), "env.example")
        with open(env_file, "r") as f:
            content = f.read()
        
        # Should have section headers and explanations
        assert "# " in content
        assert "==" in content  # Section dividers


class TestHealthCheckScripts:
    """Tests for health check scripts."""
    
    def test_health_check_script_exists(self) -> None:
        """Test that health check script exists."""
        script = os.path.join(get_project_root(), "scripts", "health_check.sh")
        assert os.path.exists(script)
    
    def test_health_check_script_executable(self) -> None:
        """Test that health check script is executable."""
        script = os.path.join(get_project_root(), "scripts", "health_check.sh")
        assert os.access(script, os.X_OK)
    
    def test_validate_config_script_exists(self) -> None:
        """Test that config validation script exists."""
        script = os.path.join(get_project_root(), "scripts", "validate_config.sh")
        assert os.path.exists(script)
    
    def test_validate_config_script_executable(self) -> None:
        """Test that config validation script is executable."""
        script = os.path.join(get_project_root(), "scripts", "validate_config.sh")
        assert os.access(script, os.X_OK)


class TestDockerfiles:
    """Tests for Dockerfile configurations."""
    
    def test_nginx_rtmp_dockerfile_exists(self) -> None:
        """Test that nginx-rtmp Dockerfile exists."""
        dockerfile = os.path.join(get_project_root(), "nginx-rtmp", "Dockerfile")
        assert os.path.exists(dockerfile)
    
    def test_nginx_rtmp_dockerfile_has_healthcheck(self) -> None:
        """Test that nginx-rtmp Dockerfile includes health check."""
        dockerfile = os.path.join(get_project_root(), "nginx-rtmp", "Dockerfile")
        with open(dockerfile, "r") as f:
            content = f.read()
        
        assert "HEALTHCHECK" in content
    
    def test_nginx_rtmp_dockerfile_exposes_ports(self) -> None:
        """Test that nginx-rtmp Dockerfile exposes required ports."""
        dockerfile = os.path.join(get_project_root(), "nginx-rtmp", "Dockerfile")
        with open(dockerfile, "r") as f:
            content = f.read()
        
        # Ports can be on same line: "EXPOSE 1935 8080"
        assert "EXPOSE" in content
        assert "1935" in content  # RTMP port
        assert "8080" in content  # HTTP port


class TestDirectoryStructure:
    """Tests for project directory structure."""
    
    def test_required_directories_exist(self) -> None:
        """Test that required directories exist."""
        required_dirs = [
            "nginx-rtmp",
            "monitoring",
            "scripts",
            "tests/unit",
            "tests/integration/shard1",
        ]
        
        for dir_name in required_dirs:
            dir_path = os.path.join(get_project_root(), dir_name)
            assert os.path.isdir(dir_path), f"Directory {dir_name} does not exist"
    
    def test_gitignore_exists(self) -> None:
        """Test that .gitignore exists."""
        gitignore = os.path.join(get_project_root(), ".gitignore")
        assert os.path.exists(gitignore)
    
    def test_gitignore_excludes_sensitive_files(self) -> None:
        """Test that .gitignore excludes sensitive files."""
        gitignore = os.path.join(get_project_root(), ".gitignore")
        with open(gitignore, "r") as f:
            content = f.read()
        
        sensitive_patterns = [".env", "*.log", "__pycache__"]
        for pattern in sensitive_patterns:
            assert pattern in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

