#!/bin/bash
set -e

echo "Starting nginx-rtmp with dynamic config..."

# Initial config fetch and generation
if [ -n "$DASHBOARD_API_URL" ] && [ -n "$API_TOKEN" ]; then
    echo "Fetching initial configuration from dashboard..."
    
    CONFIG=$(curl -s -H "Authorization: Bearer $API_TOKEN" \
        "$DASHBOARD_API_URL/api/v1/config/internal/export" || echo "{}")
    
    YOUTUBE_KEY=$(echo "$CONFIG" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('settings', {}).get('stream', {}).get('YOUTUBE_STREAM_KEY', 'dev-no-push'))")
    
    echo "Generating nginx.conf with YouTube key: ${YOUTUBE_KEY:0:10}..."
    sed "s|\${YOUTUBE_STREAM_KEY}|$YOUTUBE_KEY|g" \
        /usr/local/nginx/conf/nginx.conf.template \
        > /usr/local/nginx/conf/nginx.conf
else
    echo "Warning: No dashboard URL/token - using environment variable"
    YOUTUBE_KEY="${YOUTUBE_STREAM_KEY:-dev-no-push}"
    sed "s|\${YOUTUBE_STREAM_KEY}|$YOUTUBE_KEY|g" \
        /usr/local/nginx/conf/nginx.conf.template \
        > /usr/local/nginx/conf/nginx.conf
fi

# Start nginx in background
echo "Starting nginx..."
/usr/local/nginx/sbin/nginx

# Start Python config updater in foreground
if [ -n "$DASHBOARD_API_URL" ] && [ -n "$API_TOKEN" ]; then
    echo "Starting config auto-updater..."
    exec python3 /app/push_manager.py
else
    echo "Config auto-updater disabled - no dashboard URL"
    # Keep container running by tailing nginx logs
    tail -f /usr/local/nginx/logs/error.log
fi



