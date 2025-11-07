# Shared Libraries

This directory contains reusable libraries and utilities used across multiple services in the radio streaming system.

## Contents

### `config_client.py`

Shared configuration client for fetching dynamic configuration from the dashboard database via API.

**Usage:**

```python
from shared.config_client import DashboardConfigClient
import os

# Initialize client
config_client = DashboardConfigClient(
    dashboard_url=os.getenv("DASHBOARD_API_URL", "http://dashboard-api:9001"),
    api_token=os.getenv("API_TOKEN", ""),
    refresh_interval=60,
    service_name="my-service"
)

# Fetch configuration once
config = await config_client.fetch_config()

# Get specific setting
youtube_key = config_client.get_setting("stream", "YOUTUBE_STREAM_KEY", "default-key")

# Start auto-refresh loop
asyncio.create_task(config_client.start_auto_refresh(on_change=handle_config_change))
```

**Features:**

- ✅ Automatic refresh at configurable intervals
- ✅ Async/await support
- ✅ Error handling with logging
- ✅ Callback on configuration changes
- ✅ Thread-safe with async locks
- ✅ Service identification for logging

**Environment Variables:**

- `DASHBOARD_API_URL` - Dashboard API base URL (required)
- `API_TOKEN` - Authentication token (required)
- `CONFIG_REFRESH_INTERVAL` - Refresh interval in seconds (default: 60)

**Dependencies:**

```
httpx>=0.25.0
```

## Adding to a Service

1. Copy or mount the `shared` directory to your service container
2. Install dependencies: `pip install httpx`
3. Import and use `DashboardConfigClient`
4. Set required environment variables

## Integration Examples

### Basic Integration

```python
import asyncio
from shared.config_client import DashboardConfigClient

async def main():
    client = DashboardConfigClient(
        dashboard_url="http://dashboard-api:9001",
        api_token="your-token",
        service_name="example-service"
    )
    
    # Initial fetch
    config = await client.fetch_config()
    print(f"Config: {config}")
    
    # Start auto-refresh
    await client.start_auto_refresh()

if __name__ == "__main__":
    asyncio.run(main())
```

### With Change Callback

```python
async def on_config_change(old_config, new_config):
    """Called when configuration changes."""
    print(f"Configuration changed!")
    print(f"Old: {old_config}")
    print(f"New: {new_config}")
    
    # Reload application components
    await reload_components(new_config)

# Start with callback
await config_client.start_auto_refresh(on_change=on_config_change)
```

### Error Handling

The client handles errors gracefully:

- Network errors → Logs error, returns None, retries on next interval
- HTTP errors → Logs status code, returns None
- Invalid JSON → Logs error, returns None
- Timeout → 10 second timeout, then returns None

Your service should handle None responses:

```python
config = await client.fetch_config()
if config is None:
    # Use fallback configuration
    config = get_fallback_config()
```

## Best Practices

1. **Initialize once** - Create one client instance per service
2. **Use service name** - Makes logs easier to debug
3. **Handle None** - Always handle failed fetch scenarios
4. **Set reasonable interval** - 60 seconds is good default
5. **Log appropriately** - Client logs important events automatically
6. **Use callbacks** - React to config changes for hot-reload

## Future Enhancements

Potential improvements:

- [ ] Add caching with TTL
- [ ] Support for config schemas/validation
- [ ] Retry logic with exponential backoff
- [ ] Configuration change events via webhooks
- [ ] Support for config encryption
- [ ] Configuration versioning


