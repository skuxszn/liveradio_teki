-- ============================================================================
-- Dashboard Backend API - Database Schema
-- ============================================================================
-- Extends existing schema with dashboard-specific tables

-- ============================================================================
-- Dashboard Settings (replaces .env file management)
-- ============================================================================

CREATE TABLE IF NOT EXISTS dashboard_settings (
    id SERIAL PRIMARY KEY,
    category VARCHAR(64) NOT NULL,           -- 'stream', 'encoding', 'database', 'notifications', 'security', 'paths', 'advanced'
    key VARCHAR(128) NOT NULL,
    value TEXT,
    value_type VARCHAR(32) NOT NULL,         -- 'string', 'integer', 'boolean', 'float', 'secret', 'url', 'path'
    default_value TEXT,
    description TEXT,
    is_secret BOOLEAN DEFAULT FALSE,         -- Mask in UI, encrypt in DB
    validation_regex TEXT,                   -- Regex for validation
    validation_min NUMERIC,                  -- For numeric values
    validation_max NUMERIC,
    allowed_values JSONB,                    -- For enums/select options
    is_required BOOLEAN DEFAULT FALSE,
    requires_restart BOOLEAN DEFAULT FALSE,  -- Does changing this require stream restart?
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(category, key)
);

CREATE INDEX IF NOT EXISTS idx_settings_category ON dashboard_settings(category);

-- ============================================================================
-- Users and Authentication
-- ============================================================================

CREATE TABLE IF NOT EXISTS dashboard_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(128) UNIQUE NOT NULL,
    email VARCHAR(256) UNIQUE NOT NULL,
    password_hash VARCHAR(256) NOT NULL,     -- bcrypt hash
    full_name VARCHAR(256),
    role VARCHAR(32) DEFAULT 'viewer',       -- 'admin', 'operator', 'viewer'
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by INTEGER REFERENCES dashboard_users(id),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_username ON dashboard_users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON dashboard_users(email);

-- ============================================================================
-- JWT Tokens (for tracking/revocation)
-- ============================================================================

CREATE TABLE IF NOT EXISTS jwt_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES dashboard_users(id) ON DELETE CASCADE,
    token_hash VARCHAR(256) NOT NULL,        -- SHA256 hash of token
    token_type VARCHAR(32) NOT NULL,         -- 'access' or 'refresh'
    expires_at TIMESTAMP NOT NULL,
    revoked BOOLEAN DEFAULT FALSE,
    revoked_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT
);

CREATE INDEX IF NOT EXISTS idx_tokens_user ON jwt_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_tokens_hash ON jwt_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_tokens_expires ON jwt_tokens(expires_at);

-- ============================================================================
-- Audit Log
-- ============================================================================

CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES dashboard_users(id),
    action VARCHAR(128) NOT NULL,            -- 'stream_started', 'config_updated', 'mapping_created', etc.
    resource_type VARCHAR(64),               -- 'stream', 'mapping', 'asset', 'config', 'user'
    resource_id VARCHAR(128),
    details JSONB,                           -- Additional context
    ip_address INET,
    user_agent TEXT,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_log(resource_type, resource_id);

-- ============================================================================
-- Video Asset Metadata (extends file system storage)
-- ============================================================================

CREATE TABLE IF NOT EXISTS video_assets (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(512) UNIQUE NOT NULL,
    file_path VARCHAR(1024) NOT NULL,
    file_size BIGINT,                        -- Bytes
    duration FLOAT,                          -- Seconds
    resolution VARCHAR(32),                  -- "1280x720"
    frame_rate FLOAT,                        -- FPS
    video_codec VARCHAR(64),
    audio_codec VARCHAR(64),
    bitrate INTEGER,                         -- kbps
    pixel_format VARCHAR(32),
    is_valid BOOLEAN DEFAULT FALSE,
    validation_errors JSONB,
    thumbnail_path VARCHAR(1024),
    uploaded_by INTEGER REFERENCES dashboard_users(id),
    uploaded_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP,
    usage_count INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_assets_filename ON video_assets(filename);
CREATE INDEX IF NOT EXISTS idx_assets_valid ON video_assets(is_valid);

-- ============================================================================
-- User Sessions (for UI state persistence)
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES dashboard_users(id) ON DELETE CASCADE,
    session_key VARCHAR(128) NOT NULL,
    session_data JSONB,                      -- Store UI preferences, filters, etc.
    expires_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_key ON user_sessions(session_key);

-- ============================================================================
-- Helper Functions
-- ============================================================================

-- Function to get setting value
CREATE OR REPLACE FUNCTION get_setting(p_category VARCHAR, p_key VARCHAR)
RETURNS TEXT AS $$
DECLARE
    v_value TEXT;
BEGIN
    SELECT value INTO v_value
    FROM dashboard_settings
    WHERE category = p_category AND key = p_key;
    
    RETURN v_value;
END;
$$ LANGUAGE plpgsql;

-- Function to set setting value
CREATE OR REPLACE FUNCTION set_setting(p_category VARCHAR, p_key VARCHAR, p_value TEXT)
RETURNS VOID AS $$
BEGIN
    UPDATE dashboard_settings
    SET value = p_value, updated_at = NOW()
    WHERE category = p_category AND key = p_key;
END;
$$ LANGUAGE plpgsql;

-- Function to log audit event
CREATE OR REPLACE FUNCTION log_audit(
    p_user_id INTEGER,
    p_action VARCHAR,
    p_resource_type VARCHAR DEFAULT NULL,
    p_resource_id VARCHAR DEFAULT NULL,
    p_details JSONB DEFAULT NULL,
    p_ip_address INET DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    INSERT INTO audit_log (user_id, action, resource_type, resource_id, details, ip_address)
    VALUES (p_user_id, p_action, p_resource_type, p_resource_id, p_details, p_ip_address);
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Seed Initial Data
-- ============================================================================

-- Create default admin user (password: admin123 - CHANGE IN PRODUCTION!)
-- Password hash for 'admin123' with bcrypt 4.0.1
INSERT INTO dashboard_users (username, email, password_hash, full_name, role) VALUES
    ('admin', 'admin@localhost', '$2b$12$RhP3bjQYvakgEZlsxf5nG.oGx8o8j2uwjFcGzNnvX.eNrJiZBexHe', 'Administrator', 'admin')
ON CONFLICT (username) DO NOTHING;

-- Seed default settings with complete configuration including dropdown values
INSERT INTO dashboard_settings (category, key, value_type, description, is_required, is_secret, default_value, allowed_values, validation_min, validation_max, requires_restart) VALUES
    -- Stream settings
    ('stream', 'YOUTUBE_STREAM_KEY', 'secret', 'YouTube live stream key from YouTube Studio', TRUE, TRUE, '', NULL, NULL, NULL, TRUE),
    ('stream', 'AZURACAST_URL', 'url', 'AzuraCast server URL', TRUE, FALSE, 'http://localhost', NULL, NULL, NULL, TRUE),
    ('stream', 'AZURACAST_API_KEY', 'secret', 'AzuraCast API key for metadata fetching', TRUE, TRUE, '', NULL, NULL, NULL, TRUE),
    ('stream', 'AZURACAST_AUDIO_URL', 'url', 'Direct audio stream URL from AzuraCast', TRUE, FALSE, '', NULL, NULL, NULL, TRUE),
    ('stream', 'RTMP_ENDPOINT', 'string', 'Internal RTMP endpoint for stream relay', FALSE, FALSE, 'rtmp://nginx-rtmp:1935/live/stream', NULL, NULL, NULL, TRUE),
    
    -- Encoding settings with dropdown options
    ('encoding', 'VIDEO_RESOLUTION', 'string', 'Video resolution (width:height)', TRUE, FALSE, '1280:720', '["1920:1080", "1280:720", "854:480", "640:360"]'::jsonb, NULL, NULL, TRUE),
    ('encoding', 'VIDEO_BITRATE', 'string', 'Video bitrate (higher = better quality, more bandwidth)', TRUE, FALSE, '3000k', '["6000k", "4500k", "3000k", "2000k", "1500k"]'::jsonb, NULL, NULL, TRUE),
    ('encoding', 'AUDIO_BITRATE', 'string', 'Audio bitrate', TRUE, FALSE, '192k', '["320k", "256k", "192k", "128k", "96k"]'::jsonb, NULL, NULL, TRUE),
    ('encoding', 'VIDEO_ENCODER', 'string', 'Video encoder (libx264=CPU, h264_nvenc=NVIDIA GPU)', TRUE, FALSE, 'libx264', '["libx264", "h264_nvenc", "h264_qsv", "h264_videotoolbox"]'::jsonb, NULL, NULL, TRUE),
    ('encoding', 'FFMPEG_PRESET', 'string', 'FFmpeg encoding speed (faster = lower CPU, lower quality)', TRUE, FALSE, 'veryfast', '["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow"]'::jsonb, NULL, NULL, TRUE),
    ('encoding', 'FADE_DURATION', 'float', 'Audio/video fade transition duration (seconds)', FALSE, FALSE, '1.0', NULL, 0.0, 5.0, FALSE),
    ('encoding', 'TRACK_OVERLAP_DURATION', 'float', 'Track transition overlap duration (seconds)', FALSE, FALSE, '2.0', NULL, 0.0, 10.0, FALSE),
    ('encoding', 'FFMPEG_LOG_LEVEL', 'string', 'FFmpeg log verbosity level', FALSE, FALSE, 'info', '["quiet", "panic", "fatal", "error", "warning", "info", "verbose", "debug"]'::jsonb, NULL, NULL, FALSE),
    
    -- Logo watermark overlay settings
    ('encoding', 'ENABLE_LOGO_WATERMARK', 'boolean', 'Enable logo watermark overlay on video', FALSE, FALSE, 'false', NULL, NULL, NULL, FALSE),
    ('encoding', 'LOGO_POSITION', 'string', 'Logo position on video', FALSE, FALSE, 'top-right', '["top-left", "top-right", "bottom-left", "bottom-right"]'::jsonb, NULL, NULL, FALSE),
    ('encoding', 'LOGO_OPACITY', 'float', 'Logo opacity (0.0=invisible, 1.0=fully opaque)', FALSE, FALSE, '0.8', NULL, 0.0, 1.0, FALSE),
    
    -- Text overlay settings
    ('encoding', 'ENABLE_TEXT_OVERLAY', 'boolean', 'Enable text overlay showing track information', FALSE, FALSE, 'false', NULL, NULL, NULL, FALSE),
    
    -- Notifications
    ('notifications', 'DISCORD_WEBHOOK_URL', 'url', 'Discord webhook URL for notifications', FALSE, TRUE, '', NULL, NULL, NULL, FALSE),
    ('notifications', 'SLACK_WEBHOOK_URL', 'url', 'Slack webhook URL for notifications', FALSE, TRUE, '', NULL, NULL, NULL, FALSE),
    
    -- Database
    ('database', 'POSTGRES_HOST', 'string', 'PostgreSQL hostname', TRUE, FALSE, 'postgres', NULL, NULL, NULL, TRUE),
    ('database', 'POSTGRES_PORT', 'integer', 'PostgreSQL port', TRUE, FALSE, '5432', NULL, 1, 65535, TRUE),
    ('database', 'POSTGRES_USER', 'string', 'PostgreSQL username', TRUE, FALSE, 'radio', NULL, NULL, NULL, TRUE),
    ('database', 'POSTGRES_PASSWORD', 'secret', 'PostgreSQL password', TRUE, TRUE, '', NULL, NULL, NULL, TRUE),
    ('database', 'POSTGRES_DB', 'string', 'PostgreSQL database name', TRUE, FALSE, 'radio_db', NULL, NULL, NULL, TRUE),
    
    -- Security
    ('security', 'WEBHOOK_SECRET', 'secret', 'AzuraCast webhook validation secret', TRUE, TRUE, '', NULL, NULL, NULL, TRUE),
    ('security', 'API_TOKEN', 'secret', 'Internal API token for service-to-service communication', TRUE, TRUE, '', NULL, NULL, NULL, TRUE),
    ('security', 'JWT_SECRET', 'secret', 'JWT signing secret for dashboard authentication', TRUE, TRUE, '', NULL, NULL, NULL, TRUE),
    
    -- Paths
    ('paths', 'LOOPS_PATH', 'path', 'Video loops directory path', TRUE, FALSE, '/srv/loops', NULL, NULL, NULL, TRUE),
    ('paths', 'DEFAULT_LOOP', 'path', 'Default video loop file path', TRUE, FALSE, '/srv/loops/default.mp4', NULL, NULL, NULL, TRUE),
    ('paths', 'LOG_PATH', 'path', 'Log files directory path', FALSE, FALSE, '/var/log/radio', NULL, NULL, NULL, FALSE),
    ('paths', 'LOGO_PATH', 'path', 'Logo image file path (PNG with transparency recommended)', FALSE, FALSE, '/app/logos/logo.png', NULL, NULL, NULL, FALSE),
    
    -- Advanced
    ('advanced', 'LOG_LEVEL', 'string', 'Application logging level', FALSE, FALSE, 'INFO', '["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]'::jsonb, NULL, NULL, FALSE),
    ('advanced', 'DEBUG', 'boolean', 'Enable debug mode', FALSE, FALSE, 'false', NULL, NULL, NULL, TRUE),
    ('advanced', 'ENVIRONMENT', 'string', 'Environment name', FALSE, FALSE, 'production', '["development", "staging", "production"]'::jsonb, NULL, NULL, FALSE),
    ('advanced', 'ENABLE_METRICS', 'boolean', 'Enable Prometheus metrics export', FALSE, FALSE, 'true', NULL, NULL, NULL, TRUE),
    ('advanced', 'CONFIG_REFRESH_INTERVAL', 'integer', 'Configuration refresh interval (seconds)', FALSE, FALSE, '60', NULL, 10, 3600, FALSE),
    ('advanced', 'MAX_RESTART_ATTEMPTS', 'integer', 'Maximum FFmpeg restart attempts on failure', FALSE, FALSE, '3', NULL, 1, 10, FALSE),
    ('advanced', 'RESTART_COOLDOWN_SECONDS', 'integer', 'Cooldown period between restart attempts (seconds)', FALSE, FALSE, '60', NULL, 10, 600, FALSE)
ON CONFLICT (category, key) DO NOTHING;

