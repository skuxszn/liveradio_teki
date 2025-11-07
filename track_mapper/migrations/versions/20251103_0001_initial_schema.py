"""Initial track mapper schema

Revision ID: 20251103_0001
Revises:
Create Date: 2025-11-03 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "20251103_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create track_mappings and default_config tables."""

    # Read and execute the schema.sql file
    # In a real migration, we'd define tables explicitly with SQLAlchemy
    # For now, execute the SQL directly

    # Create track_mappings table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS track_mappings (
            id SERIAL PRIMARY KEY,
            track_key VARCHAR(512) UNIQUE NOT NULL,
            azuracast_song_id VARCHAR(128),
            loop_file_path VARCHAR(1024) NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            play_count INTEGER DEFAULT 0,
            last_played_at TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            notes TEXT
        )
    """
    )

    # Create indexes
    op.execute("CREATE INDEX IF NOT EXISTS idx_track_key ON track_mappings(track_key)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_azuracast_song_id ON track_mappings(azuracast_song_id)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_play_count ON track_mappings(play_count DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_last_played ON track_mappings(last_played_at DESC)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_active ON track_mappings(is_active) WHERE is_active = TRUE"
    )

    # Create default_config table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS default_config (
            key VARCHAR(128) PRIMARY KEY,
            value TEXT NOT NULL,
            description TEXT,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """
    )

    # Insert default configuration
    op.execute(
        """
        INSERT INTO default_config (key, value, description) VALUES
            ('default_loop', '/srv/loops/default.mp4', 'Default video loop for unmapped tracks'),
            ('cache_size', '1000', 'LRU cache size for track mappings'),
            ('cache_ttl_seconds', '3600', 'Cache TTL in seconds')
        ON CONFLICT (key) DO NOTHING
    """
    )

    # Create update trigger function
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """
    )

    # Create triggers
    op.execute(
        """
        DROP TRIGGER IF EXISTS update_track_mappings_updated_at ON track_mappings
    """
    )
    op.execute(
        """
        CREATE TRIGGER update_track_mappings_updated_at
            BEFORE UPDATE ON track_mappings
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column()
    """
    )

    op.execute(
        """
        DROP TRIGGER IF EXISTS update_default_config_updated_at ON default_config
    """
    )
    op.execute(
        """
        CREATE TRIGGER update_default_config_updated_at
            BEFORE UPDATE ON default_config
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column()
    """
    )

    # Create helper functions
    op.execute(
        """
        CREATE OR REPLACE FUNCTION normalize_track_key(artist TEXT, title TEXT)
        RETURNS VARCHAR(512) AS $$
        BEGIN
            RETURN LOWER(TRIM(artist || ' - ' || title));
        END;
        $$ LANGUAGE plpgsql IMMUTABLE
    """
    )

    op.execute(
        """
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
                (SELECT track_key FROM track_mappings
                 WHERE is_active = TRUE
                 ORDER BY play_count DESC LIMIT 1) AS most_played_track
            FROM track_mappings;
        END;
        $$ LANGUAGE plpgsql
    """
    )


def downgrade() -> None:
    """Drop all track mapper tables and functions."""

    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS update_track_mappings_updated_at ON track_mappings")
    op.execute("DROP TRIGGER IF EXISTS update_default_config_updated_at ON default_config")

    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")
    op.execute("DROP FUNCTION IF EXISTS normalize_track_key(TEXT, TEXT)")
    op.execute("DROP FUNCTION IF EXISTS get_track_stats()")

    # Drop tables
    op.execute("DROP TABLE IF EXISTS track_mappings CASCADE")
    op.execute("DROP TABLE IF EXISTS default_config CASCADE")
