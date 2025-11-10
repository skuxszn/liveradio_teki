"""Migration: add tags, created_at, updated_at columns to video_assets."""

from sqlalchemy import text

# In container, modules are imported relative to /app
from database import engine


def upgrade():
    # Use a transaction that commits automatically on success
    with engine.begin() as conn:
        # Add columns if not exists (Postgres)
        conn.execute(
            text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name='video_assets' AND column_name='tags'
                    ) THEN
                        ALTER TABLE video_assets ADD COLUMN tags JSONB;
                    END IF;
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name='video_assets' AND column_name='created_at'
                    ) THEN
                        ALTER TABLE video_assets ADD COLUMN created_at TIMESTAMP DEFAULT NOW();
                    END IF;
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name='video_assets' AND column_name='updated_at'
                    ) THEN
                        ALTER TABLE video_assets ADD COLUMN updated_at TIMESTAMP DEFAULT NOW();
                    END IF;
                END $$;
                """
            )
        )

        # Backfill timestamps from uploaded_at if present
        conn.execute(
            text(
                """
                UPDATE video_assets
                SET created_at = COALESCE(created_at, uploaded_at),
                    updated_at = COALESCE(updated_at, uploaded_at)
                """
            )
        )


def downgrade():
    # No-op (safe migration)
    pass


