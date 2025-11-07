# Security Module

**Version**: 1.0.0  
**SHARD**: 10 (Security Layer)

## Overview

The security module provides comprehensive security features for the 24/7 FFmpeg YouTube Radio Stream project, including:

- **Webhook Authentication**: Validates AzuraCast webhooks using `X-Webhook-Secret` header
- **API Authentication**: Bearer token authentication for manual control endpoints
- **Rate Limiting**: IP-based rate limiting to prevent abuse
- **License Management**: Music license tracking for compliance

## Installation

The security module is part of the main project. Ensure dependencies are installed:

```bash
pip install -r requirements-dev.txt
```

## Quick Start

### 1. Environment Configuration

Add security settings to your `.env` file:

```bash
# Security Configuration
WEBHOOK_SECRET=your-secure-webhook-secret-min-16-chars
API_TOKEN=your-secure-api-token-minimum-32-characters
WEBHOOK_RATE_LIMIT=10
API_RATE_LIMIT=60
LICENSE_MANIFEST_PATH=/srv/config/license_manifest.json
```

**Generate secure tokens**:

```bash
# Generate both tokens at once
python scripts/generate_token.py --both

# Or generate individually
python scripts/generate_token.py --type webhook
python scripts/generate_token.py --type api
```

### 2. Using Authentication in FastAPI

```python
from fastapi import Depends, FastAPI
from security.auth import validate_webhook_secret, require_api_token
from security.config import SecurityConfig

app = FastAPI()
config = SecurityConfig.from_env()

# Protect webhook endpoints
@app.post("/webhook/azuracast")
async def azuracast_webhook(
    payload: dict,
    authenticated: bool = Depends(validate_webhook_secret)
):
    # Process webhook
    return {"status": "ok"}

# Protect API endpoints
@app.post("/manual/switch")
async def manual_switch(
    track_id: str,
    authenticated: bool = Depends(require_api_token)
):
    # Manual control logic
    return {"status": "switched"}
```

### 3. Using Rate Limiting

```python
from fastapi import FastAPI, Request
from security.rate_limiter import RateLimiter, RateLimitConfig

app = FastAPI()

# Configure rate limiter
webhook_limiter = RateLimiter(
    RateLimitConfig(max_requests=10, window_seconds=60)
)

@app.post("/webhook/azuracast")
async def azuracast_webhook(request: Request, payload: dict):
    # Check rate limit
    webhook_limiter.check_rate_limit(request)
    
    # Process webhook
    return {"status": "ok"}
```

### 4. Using License Manager

```python
from security.license_manager import LicenseManager, TrackLicense

# Initialize manager
manager = LicenseManager("/srv/config/license_manifest.json")

# Add a license
license_info = TrackLicense(
    id="track_123",
    artist="Artist Name",
    title="Song Title",
    license="Creative Commons BY 4.0",
    license_url="https://creativecommons.org/licenses/by/4.0/",
    acquired_date="2025-01-15",
    notes="Licensed for streaming"
)
manager.add_license(license_info)
manager.save_manifest()

# Check if track is licensed
if manager.has_license("track_123"):
    print("Track is licensed!")

# Validate track before playing
if not manager.validate_track("track_456", "Unknown", "Song"):
    print("WARNING: Track not licensed!")

# Generate compliance report
played_tracks = ["track_123", "track_456", "track_789"]
report = manager.generate_compliance_report(played_tracks)
print(f"Compliance rate: {report['compliance_rate']}%")
```

## Module Structure

```
security/
├── __init__.py              # Module exports
├── auth.py                  # Authentication middleware
├── config.py                # Configuration management
├── license_manager.py       # License tracking
├── rate_limiter.py          # Rate limiting logic
├── README.md                # This file
└── tests/
    ├── __init__.py
    ├── test_auth.py
    ├── test_config.py
    ├── test_license_manager.py
    └── test_rate_limiter.py
```

## API Reference

### Configuration (`security.config`)

#### `SecurityConfig`

Configuration dataclass for security settings.

**Attributes**:
- `webhook_secret` (str): Secret for validating webhooks (min 16 chars)
- `api_token` (str): Bearer token for API auth (min 32 chars)
- `webhook_rate_limit` (int): Max webhook requests per minute (default: 10)
- `api_rate_limit` (int): Max API requests per minute (default: 60)
- `license_manifest_path` (str): Path to license manifest JSON
- `enable_rate_limiting` (bool): Enable/disable rate limiting (default: True)
- `enable_license_tracking` (bool): Enable/disable license tracking (default: True)

**Methods**:
- `from_env()`: Load config from environment variables
- `validate()`: Validate configuration values

**Example**:
```python
from security.config import SecurityConfig

config = SecurityConfig.from_env()
config.validate()
```

### Authentication (`security.auth`)

#### `validate_webhook_secret(x_webhook_secret, config=None)`

Validate webhook secret from `X-Webhook-Secret` header.

**Parameters**:
- `x_webhook_secret` (Optional[str]): Header value
- `config` (Optional[SecurityConfig]): Config instance

**Returns**: `bool` - True if valid

**Raises**: `WebhookAuthError` (401) if invalid

#### `require_api_token(credentials, config=None)`

Validate Bearer token for API endpoints.

**Parameters**:
- `credentials` (HTTPAuthorizationCredentials): Authorization header
- `config` (Optional[SecurityConfig]): Config instance

**Returns**: `bool` - True if valid

**Raises**: `APIAuthError` (401) if invalid

#### Async Wrappers

```python
async def validate_webhook_request(request: Request, config=None) -> bool
async def validate_api_request(request: Request, config=None) -> bool
```

### Rate Limiting (`security.rate_limiter`)

#### `RateLimitConfig`

Configuration for rate limiting.

**Attributes**:
- `max_requests` (int): Maximum requests in window
- `window_seconds` (int): Time window in seconds (default: 60)
- `enabled` (bool): Enable/disable limiting (default: True)

#### `RateLimiter`

Sliding window rate limiter.

**Methods**:
- `check_rate_limit(request)`: Check if request is within limit
- `check_rate_limit_async(request)`: Async version
- `get_remaining_requests(request)`: Get remaining request count
- `reset_limits(ip=None)`: Reset limits for IP or all IPs

**Example**:
```python
from security.rate_limiter import RateLimiter, RateLimitConfig

limiter = RateLimiter(RateLimitConfig(max_requests=10, window_seconds=60))

# In endpoint
try:
    limiter.check_rate_limit(request)
except RateLimitExceeded as e:
    # Returns 429 with Retry-After header
    raise
```

### License Management (`security.license_manager`)

#### `TrackLicense`

License information dataclass.

**Attributes**:
- `id` (str): Track identifier
- `artist` (str): Artist name
- `title` (str): Track title
- `license` (str): License type
- `license_url` (str): License URL
- `acquired_date` (str): Acquisition date (ISO format)
- `notes` (str): Optional notes

#### `LicenseManager`

Manages music license manifest.

**Methods**:
- `get_license(track_id)`: Get license for track
- `has_license(track_id)`: Check if track has license
- `add_license(license_info)`: Add/update license
- `remove_license(track_id)`: Remove license
- `validate_track(track_id, artist, title)`: Validate track license
- `get_unlicensed_tracks(played_track_ids)`: Get unlicensed tracks
- `generate_compliance_report(played_track_ids)`: Generate report
- `export_to_csv(output_path)`: Export to CSV
- `save_manifest()`: Save to file

**Example**:
```python
from security.license_manager import LicenseManager

manager = LicenseManager("/srv/config/license_manifest.json")

# Check compliance
report = manager.generate_compliance_report(played_tracks)
if report['compliance_rate'] < 100:
    print(f"Warning: {report['unlicensed_tracks']} unlicensed tracks")
```

## Scripts

### Generate Secure Token

Generate cryptographically secure tokens for API and webhook authentication.

```bash
# Generate both tokens
python scripts/generate_token.py --both

# Generate specific token type
python scripts/generate_token.py --type webhook
python scripts/generate_token.py --type api

# Custom length (minimum 16 for webhook, 32 for API)
python scripts/generate_token.py --type api --length 64

# Different character set
python scripts/generate_token.py --charset hex
python scripts/generate_token.py --charset alphanumeric

# Quiet mode (for scripting)
python scripts/generate_token.py --type api --quiet
```

### Validate Licenses

Validate license manifest and check compliance.

```bash
# Validate manifest structure
python scripts/validate_licenses.py

# Check compliance for played tracks
python scripts/validate_licenses.py --check-played

# Export manifest to CSV
python scripts/validate_licenses.py --export licenses.csv

# Export to JSON
python scripts/validate_licenses.py --export report.json --format json

# Use custom manifest path
python scripts/validate_licenses.py --manifest /path/to/manifest.json
```

## Testing

Run tests with coverage:

```bash
# Run all security tests
pytest security/tests/ -v --cov=security --cov-report=term-missing

# Run specific test file
pytest security/tests/test_auth.py -v

# Run with debugging
pytest security/tests/test_rate_limiter.py -v -s --pdb
```

**Test Coverage**: 98% (67 tests passing)

## Integration with Other Shards

### SHARD-2: Metadata Watcher Service

The metadata watcher uses webhook authentication and rate limiting:

```python
from security.auth import validate_webhook_secret
from security.rate_limiter import RateLimiter, RateLimitConfig

# In metadata_watcher/app.py
webhook_limiter = RateLimiter(RateLimitConfig(max_requests=10))

@app.post("/webhook/azuracast")
async def webhook(
    request: Request,
    payload: dict,
    authenticated: bool = Depends(validate_webhook_secret)
):
    webhook_limiter.check_rate_limit(request)
    # Process webhook
```

### SHARD-5: Logging Module

Security events are logged for auditing:

```python
from security.auth import WebhookAuthError, APIAuthError

try:
    validate_webhook_secret(secret)
except WebhookAuthError as e:
    logger.warning(
        "webhook_auth_failed",
        ip=request.client.host,
        error=str(e)
    )
```

### Integration with Play History

License tracking integrates with play history:

```python
from security.license_manager import LicenseManager
from logging_module.logger import Logger

# When track plays
if not license_manager.validate_track(track_id, artist, title):
    logger.log_error(
        service="license",
        severity="warning",
        message=f"Unlicensed track played: {track_id}"
    )
```

## Security Best Practices

1. **Token Generation**:
   - Use provided `generate_token.py` script
   - Minimum 16 characters for webhook secrets
   - Minimum 32 characters for API tokens
   - Use all character sets (alphanumeric + symbols)

2. **Token Storage**:
   - Store in `.env` file (never commit to git)
   - Use environment variables in production
   - Rotate tokens regularly (every 90 days)
   - Use different tokens for dev/staging/prod

3. **Rate Limiting**:
   - Set appropriate limits based on expected traffic
   - Monitor rate limit hits in logs
   - Adjust limits if legitimate traffic is blocked
   - Use separate limiters for different endpoint types

4. **License Compliance**:
   - Validate ALL tracks before adding to rotation
   - Generate compliance reports monthly
   - Keep license URLs and documentation
   - Export reports for auditing

5. **Monitoring**:
   - Log all authentication failures
   - Alert on repeated auth failures (potential attack)
   - Track rate limit violations
   - Monitor license compliance rate

## Troubleshooting

### Webhook Authentication Fails

**Symptoms**: 401 Unauthorized on webhook endpoint

**Solutions**:
1. Verify `WEBHOOK_SECRET` in `.env` matches AzuraCast configuration
2. Check `X-Webhook-Secret` header is being sent
3. Verify no extra whitespace in secret values
4. Test with: `curl -H "X-Webhook-Secret: your-secret" http://localhost:9000/webhook/azuracast`

### Rate Limiting Too Aggressive

**Symptoms**: Legitimate requests getting 429 errors

**Solutions**:
1. Increase `WEBHOOK_RATE_LIMIT` or `API_RATE_LIMIT` in `.env`
2. Check if behind proxy - ensure X-Forwarded-For is set correctly
3. Reset limits: `limiter.reset_limits()`
4. Disable temporarily: `config.enable_rate_limiting = False`

### License Manifest Not Found

**Symptoms**: LicenseManifestError on startup

**Solutions**:
1. Verify `LICENSE_MANIFEST_PATH` is correct
2. Ensure directory exists and is writable
3. Run: `python scripts/validate_licenses.py` to create empty manifest
4. Check file permissions

## Performance Considerations

- **Authentication**: Uses constant-time comparison (protection against timing attacks)
- **Rate Limiting**: O(1) per request with sliding window cleanup
- **License Manager**: LRU caching (1000 entries) for database queries
- **Memory Usage**: ~1MB for 10,000 tracked IPs in rate limiter

## Known Limitations

1. **Rate Limiting**: In-memory storage (resets on restart) - use Redis for distributed systems
2. **License Manager**: Requires manual addition of licenses - no auto-discovery
3. **Token Rotation**: Manual process - no automatic rotation yet

## Future Enhancements

- OAuth2 support for third-party integrations
- JWT token support for stateless authentication
- Redis backend for distributed rate limiting
- Automatic license validation via API lookup
- RBAC (Role-Based Access Control) for different user types
- Audit log export to external systems

## Contributing

When modifying the security module:

1. Write tests first (TDD)
2. Maintain >80% code coverage
3. Run linters: `black`, `flake8`, `mypy`
4. Update this README with API changes
5. Add security audit entries for breaking changes

## License

Part of the 24/7 FFmpeg YouTube Radio Stream project.

## Support

For issues or questions:
- Check logs in `/var/log/radio/`
- Review `docs/SECURITY.md` for best practices
- Generate token: `python scripts/generate_token.py --help`
- Validate licenses: `python scripts/validate_licenses.py --help`

---

**Last Updated**: November 5, 2025  
**Module Version**: 1.0.0  
**Test Coverage**: 98%  
**SHARD Status**: ✅ Complete



