-- Logging & Analytics Module Database Schema (SHARD-5)
-- PostgreSQL 15+ compatible

-- ============================================================================
-- Play History - Track play session logging
-- ============================================================================

CREATE TABLE IF NOT EXISTS play_history (
    id SERIAL PRIMARY KEY,
    track_key VARCHAR(512) NOT NULL,             -- Normalized "artist - title"
    artist VARCHAR(256),                         -- Artist name
    title VARCHAR(256),                          -- Song title
    album VARCHAR(256),                          -- Album name (optional)
    azuracast_song_id VARCHAR(128),             -- AzuraCast song ID (optional)
    loop_file_path VARCHAR(1024),               -- MP4 loop file used
    started_at TIMESTAMP NOT NULL,               -- When track started playing
    ended_at TIMESTAMP,                          -- When track ended (NULL if still playing)
    duration_seconds INTEGER,                    -- Actual play duration
    expected_duration_seconds INTEGER,           -- Track duration from metadata
    ffmpeg_pid INTEGER,                          -- FFmpeg process ID
    had_errors BOOLEAN DEFAULT FALSE,            -- Whether errors occurred during play
    error_message TEXT,                          -- Error details (if any)
    error_count INTEGER DEFAULT 0,               -- Number of errors during this play session
    metadata JSONB                               -- Additional metadata (flexible)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_play_history_started ON play_history(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_play_history_track_key ON play_history(track_key);
CREATE INDEX IF NOT EXISTS idx_play_history_artist ON play_history(artist);
CREATE INDEX IF NOT EXISTS idx_play_history_errors ON play_history(had_errors) WHERE had_errors = TRUE;
CREATE INDEX IF NOT EXISTS idx_play_history_ended ON play_history(ended_at DESC NULLS FIRST);

-- ============================================================================
-- Error Log - System-wide error tracking
-- ============================================================================

CREATE TABLE IF NOT EXISTS error_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),  -- When error occurred
    service VARCHAR(64) NOT NULL,                -- Service: 'ffmpeg', 'watcher', 'rtmp', etc.
    severity VARCHAR(16) NOT NULL,               -- Severity: 'info', 'warning', 'error', 'critical'
    message TEXT NOT NULL,                       -- Error message
    context JSONB,                               -- Additional context (flexible)
    stack_trace TEXT,                            -- Stack trace (if available)
    resolved BOOLEAN DEFAULT FALSE,              -- Whether error was resolved
    resolved_at TIMESTAMP,                       -- When error was resolved
    play_history_id INTEGER,                     -- Link to play_history if applicable
    CONSTRAINT fk_play_history FOREIGN KEY (play_history_id) 
        REFERENCES play_history(id) ON DELETE SET NULL
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_error_log_timestamp ON error_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_error_log_service ON error_log(service);
CREATE INDEX IF NOT EXISTS idx_error_log_severity ON error_log(severity);
CREATE INDEX IF NOT EXISTS idx_error_log_resolved ON error_log(resolved) WHERE resolved = FALSE;

-- ============================================================================
-- System Metrics - Performance and uptime tracking
-- ============================================================================

CREATE TABLE IF NOT EXISTS system_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    metric_name VARCHAR(128) NOT NULL,           -- Metric name (e.g., 'cpu_usage', 'memory_mb')
    metric_value NUMERIC NOT NULL,               -- Metric value
    unit VARCHAR(32),                            -- Unit (e.g., 'percent', 'MB', 'seconds')
    service VARCHAR(64),                         -- Service name (optional)
    metadata JSONB                               -- Additional metadata
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp ON system_metrics(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_system_metrics_name ON system_metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_system_metrics_service ON system_metrics(service);

-- ============================================================================
-- Update Trigger for ended_at
-- ============================================================================

-- Function to calculate duration when play session ends
CREATE OR REPLACE FUNCTION calculate_play_duration()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.ended_at IS NOT NULL AND OLD.ended_at IS NULL THEN
        NEW.duration_seconds = EXTRACT(EPOCH FROM (NEW.ended_at - NEW.started_at))::INTEGER;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for play_history duration calculation
DROP TRIGGER IF EXISTS calculate_play_duration_trigger ON play_history;
CREATE TRIGGER calculate_play_duration_trigger
    BEFORE UPDATE ON play_history
    FOR EACH ROW
    EXECUTE FUNCTION calculate_play_duration();

-- ============================================================================
-- Helper Functions
-- ============================================================================

-- Function to get play statistics for a date range
CREATE OR REPLACE FUNCTION get_play_stats(
    start_date TIMESTAMP DEFAULT NOW() - INTERVAL '7 days',
    end_date TIMESTAMP DEFAULT NOW()
)
RETURNS TABLE(
    total_plays BIGINT,
    unique_tracks BIGINT,
    total_duration_hours NUMERIC,
    avg_duration_seconds NUMERIC,
    error_rate NUMERIC,
    uptime_percent NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::BIGINT AS total_plays,
        COUNT(DISTINCT track_key)::BIGINT AS unique_tracks,
        (SUM(COALESCE(duration_seconds, 0)) / 3600.0)::NUMERIC AS total_duration_hours,
        AVG(COALESCE(duration_seconds, 0))::NUMERIC AS avg_duration_seconds,
        (COUNT(*) FILTER (WHERE had_errors = TRUE)::NUMERIC / NULLIF(COUNT(*), 0) * 100)::NUMERIC AS error_rate,
        ((COUNT(*) FILTER (WHERE had_errors = FALSE)::NUMERIC / NULLIF(COUNT(*), 0)) * 100)::NUMERIC AS uptime_percent
    FROM play_history
    WHERE started_at >= start_date AND started_at <= end_date;
END;
$$ LANGUAGE plpgsql;

-- Function to get most played tracks
CREATE OR REPLACE FUNCTION get_most_played_tracks(
    start_date TIMESTAMP DEFAULT NOW() - INTERVAL '7 days',
    end_date TIMESTAMP DEFAULT NOW(),
    limit_count INTEGER DEFAULT 10
)
RETURNS TABLE(
    track_key VARCHAR(512),
    artist VARCHAR(256),
    title VARCHAR(256),
    play_count BIGINT,
    total_duration_hours NUMERIC,
    error_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ph.track_key,
        ph.artist,
        ph.title,
        COUNT(*)::BIGINT AS play_count,
        (SUM(COALESCE(ph.duration_seconds, 0)) / 3600.0)::NUMERIC AS total_duration_hours,
        SUM(ph.error_count)::BIGINT AS error_count
    FROM play_history ph
    WHERE ph.started_at >= start_date AND ph.started_at <= end_date
    GROUP BY ph.track_key, ph.artist, ph.title
    ORDER BY play_count DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get error summary by service
CREATE OR REPLACE FUNCTION get_error_summary(
    start_date TIMESTAMP DEFAULT NOW() - INTERVAL '7 days',
    end_date TIMESTAMP DEFAULT NOW()
)
RETURNS TABLE(
    service VARCHAR(64),
    severity VARCHAR(16),
    error_count BIGINT,
    resolved_count BIGINT,
    unresolved_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        el.service,
        el.severity,
        COUNT(*)::BIGINT AS error_count,
        COUNT(*) FILTER (WHERE el.resolved = TRUE)::BIGINT AS resolved_count,
        COUNT(*) FILTER (WHERE el.resolved = FALSE)::BIGINT AS unresolved_count
    FROM error_log el
    WHERE el.timestamp >= start_date AND el.timestamp <= end_date
    GROUP BY el.service, el.severity
    ORDER BY error_count DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to get hourly play distribution
CREATE OR REPLACE FUNCTION get_hourly_play_distribution(
    start_date TIMESTAMP DEFAULT NOW() - INTERVAL '7 days',
    end_date TIMESTAMP DEFAULT NOW()
)
RETURNS TABLE(
    hour_of_day INTEGER,
    play_count BIGINT,
    avg_duration_seconds NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        EXTRACT(HOUR FROM started_at)::INTEGER AS hour_of_day,
        COUNT(*)::BIGINT AS play_count,
        AVG(COALESCE(duration_seconds, 0))::NUMERIC AS avg_duration_seconds
    FROM play_history
    WHERE started_at >= start_date AND started_at <= end_date
    GROUP BY hour_of_day
    ORDER BY hour_of_day;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Data Retention Functions
-- ============================================================================

-- Function to archive old play history (>90 days)
CREATE OR REPLACE FUNCTION archive_old_play_history(days_to_keep INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM play_history
    WHERE started_at < NOW() - (days_to_keep || ' days')::INTERVAL
    RETURNING id INTO deleted_count;
    
    RETURN COALESCE(deleted_count, 0);
END;
$$ LANGUAGE plpgsql;

-- Function to clean resolved errors (>30 days)
CREATE OR REPLACE FUNCTION clean_resolved_errors(days_to_keep INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM error_log
    WHERE resolved = TRUE 
      AND resolved_at < NOW() - (days_to_keep || ' days')::INTERVAL
    RETURNING id INTO deleted_count;
    
    RETURN COALESCE(deleted_count, 0);
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Views
-- ============================================================================

-- View for recent plays (last 100)
CREATE OR REPLACE VIEW recent_plays AS
SELECT 
    id,
    track_key,
    artist,
    title,
    album,
    started_at,
    ended_at,
    duration_seconds,
    had_errors,
    error_message,
    ffmpeg_pid
FROM play_history
ORDER BY started_at DESC
LIMIT 100;

-- View for current playing track
CREATE OR REPLACE VIEW current_playing AS
SELECT 
    id,
    track_key,
    artist,
    title,
    album,
    loop_file_path,
    started_at,
    ffmpeg_pid,
    (EXTRACT(EPOCH FROM (NOW() - started_at)))::INTEGER AS elapsed_seconds
FROM play_history
WHERE ended_at IS NULL
ORDER BY started_at DESC
LIMIT 1;

-- ============================================================================
-- Comments
-- ============================================================================

COMMENT ON TABLE play_history IS 'Logs every track play session for analytics and debugging';
COMMENT ON COLUMN play_history.track_key IS 'Normalized track identifier: "artist - title" (lowercase)';
COMMENT ON COLUMN play_history.duration_seconds IS 'Actual play duration (calculated when ended_at is set)';
COMMENT ON COLUMN play_history.had_errors IS 'TRUE if any errors occurred during playback';
COMMENT ON COLUMN play_history.metadata IS 'Flexible JSONB field for additional track metadata';

COMMENT ON TABLE error_log IS 'System-wide error tracking for all services';
COMMENT ON COLUMN error_log.severity IS 'Error severity: info, warning, error, critical';
COMMENT ON COLUMN error_log.context IS 'Flexible JSONB field for error context and debugging data';

COMMENT ON TABLE system_metrics IS 'Time-series metrics for system performance monitoring';

COMMENT ON FUNCTION get_play_stats IS 'Returns aggregate statistics for a date range';
COMMENT ON FUNCTION get_most_played_tracks IS 'Returns top N most played tracks in date range';
COMMENT ON FUNCTION get_error_summary IS 'Returns error counts grouped by service and severity';
COMMENT ON FUNCTION get_hourly_play_distribution IS 'Returns play counts by hour of day';

-- ============================================================================
-- Initial Data
-- ============================================================================

-- Insert example data retention configuration into default_config if it exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'default_config') THEN
        INSERT INTO default_config (key, value, description) VALUES
            ('play_history_retention_days', '90', 'Number of days to keep play history'),
            ('error_log_retention_days', '30', 'Number of days to keep resolved errors'),
            ('metrics_retention_days', '30', 'Number of days to keep system metrics')
        ON CONFLICT (key) DO NOTHING;
    END IF;
END $$;



