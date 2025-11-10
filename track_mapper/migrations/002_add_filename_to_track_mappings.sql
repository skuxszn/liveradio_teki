-- Migration: Add filename column and backfill from loop_file_path
-- Safe, backward-compatible change. Do NOT drop loop_file_path yet.

ALTER TABLE track_mappings
    ADD COLUMN IF NOT EXISTS filename VARCHAR(512);

-- Backfill filename from loop_file_path basename when filename is NULL or empty
UPDATE track_mappings
SET filename = COALESCE(
    NULLIF(regexp_replace(loop_file_path, '^.*/', ''), ''),
    filename
)
WHERE (filename IS NULL OR filename = '') AND loop_file_path IS NOT NULL;

-- Optional index to speed up lookups by filename
CREATE INDEX IF NOT EXISTS idx_track_mappings_filename ON track_mappings(filename);



