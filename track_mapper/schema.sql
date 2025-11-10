-- Track Mapper Database Schema (SHARD-3)
-- PostgreSQL 15+ compatible

-- ============================================================================
-- Track to Video Loop Mappings
-- ============================================================================

CREATE TABLE IF NOT EXISTS track_mappings (
    id SERIAL PRIMARY KEY,
    track_key VARCHAR(512) UNIQUE NOT NULL,  -- "artist - title" normalized
    azuracast_song_id VARCHAR(128),          -- AzuraCast song ID (optional)
    loop_file_path VARCHAR(1024) NOT NULL,   -- Absolute path to MP4 loop
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    play_count INTEGER DEFAULT 0,
    last_played_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,          -- Flag for soft delete
    notes TEXT                                -- Optional notes/metadata
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_track_key ON track_mappings(track_key);
CREATE INDEX IF NOT EXISTS idx_azuracast_song_id ON track_mappings(azuracast_song_id);
CREATE INDEX IF NOT EXISTS idx_play_count ON track_mappings(play_count DESC);
CREATE INDEX IF NOT EXISTS idx_last_played ON track_mappings(last_played_at DESC);
CREATE INDEX IF NOT EXISTS idx_active ON track_mappings(is_active) WHERE is_active = TRUE;

-- ============================================================================
-- Default Configuration
-- ============================================================================

CREATE TABLE IF NOT EXISTS default_config (
    key VARCHAR(128) PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Insert default loop configuration
INSERT INTO default_config (key, value, description) VALUES
    ('default_loop', '/srv/loops/default.mp4', 'Default video loop for unmapped tracks'),
    ('cache_size', '1000', 'LRU cache size for track mappings'),
    ('cache_ttl_seconds', '3600', 'Cache TTL in seconds')
ON CONFLICT (key) DO NOTHING;

-- ============================================================================
-- Update Trigger for updated_at
-- ============================================================================

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for track_mappings
DROP TRIGGER IF EXISTS update_track_mappings_updated_at ON track_mappings;
CREATE TRIGGER update_track_mappings_updated_at
    BEFORE UPDATE ON track_mappings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for default_config
DROP TRIGGER IF EXISTS update_default_config_updated_at ON default_config;
CREATE TRIGGER update_default_config_updated_at
    BEFORE UPDATE ON default_config
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Helper Functions
-- ============================================================================

-- Function to normalize track key (lowercase, strip whitespace)
CREATE OR REPLACE FUNCTION normalize_track_key(artist TEXT, title TEXT)
RETURNS VARCHAR(512) AS $$
BEGIN
    RETURN LOWER(TRIM(artist || ' - ' || title));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to get track statistics
CREATE OR REPLACE FUNCTION get_track_stats()
RETURNS TABLE(
    total_tracks BIGINT,
    active_tracks BIGINT,
    total_plays BIGINT,
    avg_plays_per_track NUMERIC,
    most_played_track VARCHAR(512)
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::BIGINT AS total_tracks,
        COUNT(*) FILTER (WHERE is_active = TRUE)::BIGINT AS active_tracks,
        SUM(play_count)::BIGINT AS total_plays,
        AVG(play_count)::NUMERIC AS avg_plays_per_track,
        (SELECT track_key FROM track_mappings WHERE is_active = TRUE ORDER BY play_count DESC LIMIT 1) AS most_played_track
    FROM track_mappings;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Comments
-- ============================================================================

COMMENT ON TABLE track_mappings IS 'Maps tracks to video loop files for 24/7 radio stream';
COMMENT ON COLUMN track_mappings.track_key IS 'Normalized track identifier: "artist - title" (lowercase)';
COMMENT ON COLUMN track_mappings.azuracast_song_id IS 'AzuraCast song ID for direct lookup';
COMMENT ON COLUMN track_mappings.loop_file_path IS 'Absolute path to MP4 video loop file';
COMMENT ON COLUMN track_mappings.play_count IS 'Number of times this track has been played';
COMMENT ON COLUMN track_mappings.is_active IS 'FALSE for soft-deleted mappings';

COMMENT ON TABLE default_config IS 'System-wide configuration key-value pairs';
COMMENT ON FUNCTION normalize_track_key IS 'Normalizes artist and title into a consistent track key';
COMMENT ON FUNCTION get_track_stats IS 'Returns statistics about track mappings';





