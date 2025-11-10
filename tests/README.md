# Testing Suite - 24/7 FFmpeg YouTube Radio Stream

Comprehensive testing infrastructure for SHARD-11, providing unit tests, integration tests, load tests, and failover tests.

## Overview

This testing suite provides:

- **Unit Tests**: Test individual modules in isolation (>80% coverage target)
- **Integration Tests**: Test end-to-end workflows and service interactions
- **Load Tests**: Performance testing with Locust (1000 track switches, 24-hour streams)
- **Failover Tests**: Auto-recovery and disaster recovery scenarios
- **Test Fixtures**: Mock data, sample payloads, and test video loops
- **CI/CD Pipeline**: Automated testing on GitHub Actions
- **Test Environment**: Isolated Docker Compose environment

## Quick Start

### 1. Install Dependencies

```bash
# Activate virtual environment
source venv/bin/activate

# Install test dependencies
pip install -r requirements-dev.txt
```

### 2. Run All Tests

```bash
# Run the comprehensive test suite
./scripts/run_all_tests.sh --all --coverage --html
```

### 3. View Coverage Report

```bash
# Open HTML coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared pytest fixtures
├── README.md                # This file
│
├── unit/                    # Unit tests (fast, no external dependencies)
│   ├── metadata_watcher/
│   ├── track_mapper/
│   └── test_config_validation.py
│
├── integration/             # Integration tests (require Docker)
│   ├── metadata_watcher/
│   ├── track_mapper/
│   ├── shard1/
│   ├── test_end_to_end.py
│   └── test_full_stack.py
│
├── load/                    # Load tests (Locust)
│   ├── __init__.py
│   ├── locustfile.py
│   └── README.md
│
├── failover/                # Failover and recovery tests
│   ├── __init__.py
│   ├── test_ffmpeg_recovery.py
│   ├── test_service_recovery.py
│   └── README.md
│
└── fixtures/                # Test data and mocks
    ├── __init__.py
    ├── sample_data.py
    ├── generate_test_video.py
    ├── loops/               # Test video files
    └── payloads/            # Sample JSON payloads
        ├── azuracast_webhook.json
        └── azuracast_webhook_minimal.json
```

## Running Tests

### Unit Tests Only (Fast)

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run specific module
pytest tests/unit/metadata_watcher/ -v

# Run with coverage
pytest tests/unit/ --cov=. --cov-report=term-missing
```

### Integration Tests

```bash
# Start Docker test environment
docker-compose -f docker-compose.test.yml up -d

# Run integration tests
pytest tests/integration/ -v -m integration

# Stop Docker environment
docker-compose -f docker-compose.test.yml down -v
```

### Load Tests

```bash
# Start services
docker-compose -f docker-compose.test.yml up -d

# Run load tests (interactive)
locust -f tests/load/locustfile.py --host=http://localhost:9001

# Run load tests (headless)
locust -f tests/load/locustfile.py \
    --host=http://localhost:9001 \
    --users 10 \
    --spawn-rate 2 \
    --run-time 5m \
    --headless
```

### Failover Tests

```bash
# Run all failover tests
pytest tests/failover/ -v

# Run only fast failover tests (skip slow)
pytest tests/failover/ -v -m "not slow"

# Run specific scenario
pytest tests/failover/test_ffmpeg_recovery.py::TestFFmpegAutoRecovery::test_ffmpeg_crash_triggers_restart -v
```

### Test Markers

Use pytest markers to run specific test categories:

```bash
# Run only unit tests
pytest -m unit -v

# Run only integration tests
pytest -m integration -v

# Run only tests that don't require Docker
pytest -m "not requires_docker" -v

# Run only fast tests (skip slow)
pytest -m "not slow" -v

# Combine markers
pytest -m "integration and not slow" -v
```

## Using the Test Runner Script

The `scripts/run_all_tests.sh` script provides a convenient way to run tests:

```bash
# Show help
./scripts/run_all_tests.sh --help

# Run unit tests only
./scripts/run_all_tests.sh --unit-only

# Run unit + integration tests
./scripts/run_all_tests.sh --integration

# Run all tests (including slow tests)
./scripts/run_all_tests.sh --all

# Run with coverage report
./scripts/run_all_tests.sh --all --coverage --html

# Start Docker, run tests, stop Docker
./scripts/run_all_tests.sh --docker-start --all --docker-stop

# Skip Docker-dependent tests
./scripts/run_all_tests.sh --skip-docker

# Run load tests
./scripts/run_all_tests.sh --load-test
```

## Test Fixtures

### Sample Data

The `tests/fixtures/sample_data.py` module provides:

```python
from tests.fixtures.sample_data import (
    get_azuracast_webhook_payload,    # Full webhook payload
    get_minimal_webhook_payload,       # Minimal webhook payload
    get_sample_track_metadata,         # List of track metadata
    get_sample_error_events,           # Error event samples
    get_sample_ffmpeg_command,         # FFmpeg command example
    get_sample_env_vars,               # Environment variables
    get_prometheus_metrics_sample,     # Prometheus metrics
)
```

### Generating Test Videos

```bash
# Generate test video loops
python tests/fixtures/generate_test_video.py

# This creates:
# - tests/fixtures/loops/default.mp4
# - tests/fixtures/loops/track_123_loop.mp4
# - tests/fixtures/loops/track_456_loop.mp4
# - tests/fixtures/loops/track_789_loop.mp4
# - tests/fixtures/loops/invalid_resolution.mp4
# - tests/fixtures/loops/corrupt.mp4
```

## Docker Test Environment

The `docker-compose.test.yml` provides an isolated test environment:

```bash
# Start test environment
docker-compose -f docker-compose.test.yml up -d

# Check service health
docker-compose -f docker-compose.test.yml ps

# View logs
docker-compose -f docker-compose.test.yml logs -f

# Stop and clean up
docker-compose -f docker-compose.test.yml down -v
```

### Test Services

- **postgres-test**: PostgreSQL 15 on port 5433
- **nginx-rtmp-test**: nginx-rtmp on port 1936
- **prometheus-test**: Prometheus on port 9091
- **metadata-watcher-test**: Metadata watcher on port 9001

## CI/CD Pipeline

The `.github/workflows/ci.yml` pipeline runs automatically on:
- Push to `main` or `develop` branches
- Pull requests
- Manual workflow dispatch

### Pipeline Jobs

1. **Lint**: Code quality checks (Black, Flake8, mypy)
2. **Unit Tests**: Fast unit tests
3. **Integration Tests**: Tests with PostgreSQL
4. **Coverage**: Code coverage report (must be ≥80%)
5. **Docker Build**: Test Docker image builds
6. **Load Tests**: Performance tests (main branch only)
7. **Security**: Trivy vulnerability scan

### Viewing CI Results

- Test results are uploaded as artifacts
- Coverage reports available in Codecov
- Security scan results in GitHub Security tab

## Coverage Requirements

SHARD-11 requires ≥80% code coverage.

### Check Coverage

```bash
# Run tests with coverage
pytest --cov=. --cov-report=term-missing

# Generate HTML report
pytest --cov=. --cov-report=html
open htmlcov/index.html

# Fail if coverage below threshold
pytest --cov=. --cov-report=term-missing --cov-fail-under=80
```

### Coverage Configuration

Coverage settings are in `pytest.ini`:

```ini
[coverage:run]
source = .
omit =
    */tests/*
    */venv/*
    */__pycache__/*
    */site-packages/*

[coverage:report]
precision = 2
show_missing = True
skip_covered = False
```

## Testing Best Practices

### 1. Test Isolation

Each test should be independent:

```python
@pytest.fixture
def clean_database():
    """Provide a clean database for each test."""
    # Setup
    db = create_test_database()
    yield db
    # Teardown
    db.drop_all()
```

### 2. Mock External Dependencies

```python
@pytest.fixture
def mock_azuracast(monkeypatch):
    """Mock AzuraCast API calls."""
    def fake_get(*args, **kwargs):
        return MockResponse({"now_playing": {...}})
    monkeypatch.setattr(requests, "get", fake_get)
```

### 3. Use Markers

```python
@pytest.mark.integration
@pytest.mark.requires_docker
@pytest.mark.slow
def test_24_hour_stream():
    """Test 24-hour continuous operation."""
    pass
```

### 4. Parametrize Tests

```python
@pytest.mark.parametrize("artist,title,expected", [
    ("Artist1", "Song1", "/srv/loops/track1.mp4"),
    ("Artist2", "Song2", "/srv/loops/track2.mp4"),
])
def test_track_mapping(artist, title, expected):
    mapper = TrackMapper()
    result = mapper.get_loop(artist, title)
    assert result == expected
```

### 5. Test Error Cases

```python
def test_invalid_webhook_returns_422():
    """Test that invalid webhook returns 422."""
    response = client.post("/webhook/azuracast", json={})
    assert response.status_code == 422
```

## Troubleshooting

### Tests Fail with "Docker not available"

```bash
# Verify Docker is running
docker ps

# Start Docker test environment
docker-compose -f docker-compose.test.yml up -d

# Or skip Docker tests
pytest -m "not requires_docker"
```

### Import Errors

```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Install dependencies
pip install -r requirements-dev.txt

# Add project to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Database Connection Errors

```bash
# Check PostgreSQL is running
docker-compose -f docker-compose.test.yml ps postgres-test

# Verify credentials
psql -h localhost -p 5433 -U test_radio -d test_radio_db

# Recreate database
docker-compose -f docker-compose.test.yml down -v
docker-compose -f docker-compose.test.yml up -d
```

### Coverage Below 80%

```bash
# See which files need more tests
pytest --cov=. --cov-report=term-missing

# Generate HTML report for detailed view
pytest --cov=. --cov-report=html
open htmlcov/index.html

# Focus on untested modules
pytest path/to/module --cov=path/to/module --cov-report=term-missing
```

### Slow Tests

```bash
# Skip slow tests
pytest -m "not slow"

# Show slowest tests
pytest --durations=10

# Set timeout for tests
pytest --timeout=300  # 5 minute timeout
```

## Success Criteria (SHARD-11)

✅ **All tests pass**
- Unit tests: All passing
- Integration tests: All passing in clean environment
- Failover tests: All recovery scenarios tested

✅ **Load tests pass**
- 1000 track switches: No crashes
- 24-hour stream: <0.1% downtime
- Performance: Acceptable response times

✅ **Code coverage ≥80%**
- Overall coverage: ≥80%
- Per-module coverage: ≥70%
- Critical paths: 100%

✅ **Documentation complete**
- Test README: Complete
- Module documentation: Complete
- Usage examples: Provided

✅ **CI/CD pipeline**
- Automated testing: Configured
- Test results: Uploaded
- Coverage reporting: Integrated

## Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [Locust Documentation](https://docs.locust.io/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [GitHub Actions Documentation](https://docs.github.com/actions)

## Support

For issues or questions:
1. Check this README
2. Review module-specific test README files
3. Check GitHub Issues
4. Create new issue with test failure details

---

**SHARD-11: Testing Suite**  
**Status**: Complete ✓  
**Coverage**: ≥80% ✓  
**Last Updated**: November 5, 2025




