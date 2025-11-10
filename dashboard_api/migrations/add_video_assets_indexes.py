"""Add performant indexes for video_assets search and sorting."""

from sqlalchemy import text

from database import engine


def upgrade():
    """Create indexes if not exist (idempotent)."""
    with engine.begin() as conn:
        # Create GIN index on tags (Postgres)
        conn.execute(
            text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_indexes WHERE indexname = 'idx_video_assets_tags_gin'
                    ) THEN
                        CREATE INDEX idx_video_assets_tags_gin ON video_assets USING GIN (tags);
                    END IF;
                END $$;
                """
            )
        )
        # Optimize filename LIKE queries with text_pattern_ops
        conn.execute(
            text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_indexes WHERE indexname = 'idx_video_assets_filename_pattern'
                    ) THEN
                        CREATE INDEX idx_video_assets_filename_pattern
                        ON video_assets (filename text_pattern_ops);
                    END IF;
                END $$;
                """
            )
        )


def downgrade():
    # Safe no-op
    pass


