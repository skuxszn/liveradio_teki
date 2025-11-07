#!/bin/sh
set -e

# Ensure writable dirs are owned by radiouser (uid 1000)
chown -R 1000:1000 /app/stream /var/log/radio 2>/dev/null || true

# Drop privileges and run the app
exec su -s /bin/sh -c "python -m uvicorn metadata_watcher.app:app --host 0.0.0.0 --port 9000" radiouser


