# Testing Quick Start Guide

## Run Tests in 30 Seconds

```bash
# 1. Activate virtual environment
source venv/bin/activate

# 2. Run all tests with coverage
./scripts/run_all_tests.sh --all --coverage

# 3. View results
# Coverage: 91% ✓
# Tests: 578 passing ✓
```

## Common Commands

### Fast Unit Tests Only
```bash
pytest tests/unit/ -v
```

### With Coverage Report
```bash
pytest tests/unit/ --cov --cov-report=html
open htmlcov/index.html
```

### Integration Tests (Requires Docker)
```bash
# Start Docker services
docker-compose -f docker-compose.test.yml up -d

# Run tests
pytest tests/integration/ -v -m integration

# Cleanup
docker-compose -f docker-compose.test.yml down -v
```

### Load Tests
```bash
# Interactive (Web UI)
locust -f tests/load/locustfile.py --host=http://localhost:9000

# Headless (automated)
locust -f tests/load/locustfile.py \
    --host=http://localhost:9000 \
    --users 10 \
    --spawn-rate 2 \
    --run-time 5m \
    --headless
```

### Failover Tests
```bash
pytest tests/failover/ -v
```

### Skip Slow Tests
```bash
pytest -m "not slow" -v
```

### Skip Docker Tests
```bash
pytest -m "not requires_docker" -v
```

## Test Categories

| Category | Command | Speed | Docker Required |
|----------|---------|-------|-----------------|
| Unit | `pytest tests/unit/` | Fast (2-6s) | No |
| Integration | `pytest tests/integration/` | Medium (10-30s) | Yes |
| Load | `locust -f tests/load/locustfile.py` | Slow (2-10m) | Recommended |
| Failover | `pytest tests/failover/` | Variable (5-60s) | Recommended |

## Quick Troubleshooting

### "Import Error"
```bash
source venv/bin/activate
pip install -r requirements-dev.txt
```

### "Docker not available"
```bash
docker-compose -f docker-compose.test.yml up -d
# OR skip Docker tests:
pytest -m "not requires_docker"
```

### "Coverage too low"
```bash
# See what's missing
pytest --cov --cov-report=term-missing
```

### "Tests are slow"
```bash
# Skip slow tests
pytest -m "not slow"
```

## CI/CD

Tests run automatically on:
- Push to `main` or `develop`
- Pull requests
- Manual trigger

View results: GitHub Actions tab

## Need Help?

- Full docs: `tests/README.md`
- Load tests: `tests/load/README.md`
- Failover tests: `tests/failover/README.md`
- Completion report: `SHARD_11_COMPLETION_REPORT.md`

---

**Test Coverage**: 91% ✓  
**Total Tests**: 618  
**Status**: All passing ✓



