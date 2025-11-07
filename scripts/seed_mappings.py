#!/usr/bin/env python3
"""Seed Track Mappings - Bulk import track-to-loop mappings

Supports importing from:
- JSON file
- CSV file
- Directory scanning (auto-detect loops)

Usage:
    python scripts/seed_mappings.py --json mappings.json
    python scripts/seed_mappings.py --csv mappings.csv
    python scripts/seed_mappings.py --scan /srv/loops/tracks
"""

import argparse
import csv
import json
import logging
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from track_mapper.config import TrackMapperConfig  # noqa: E402
from track_mapper.mapper import TrackMapper  # noqa: E402

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_json_mappings(json_file: str) -> List[Dict[str, Any]]:
    """Load mappings from JSON file.

    Expected format:
    [
        {
            "artist": "Artist Name",
            "title": "Song Title",
            "loop_path": "/srv/loops/tracks/track.mp4",
            "song_id": "123",
            "notes": "Optional notes"
        },
        ...
    ]

    Args:
        json_file: Path to JSON file

    Returns:
        List of mapping dictionaries
    """
    logger.info(f"Loading mappings from JSON: {json_file}")
    with open(json_file, "r") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("JSON must contain a list of mappings")

    logger.info(f"Loaded {len(data)} mappings from JSON")
    return data


def load_csv_mappings(csv_file: str) -> List[Dict[str, Any]]:
    """Load mappings from CSV file.

    Expected columns: artist,title,loop_path,song_id,notes

    Args:
        csv_file: Path to CSV file

    Returns:
        List of mapping dictionaries
    """
    logger.info(f"Loading mappings from CSV: {csv_file}")
    mappings = []

    with open(csv_file, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            mappings.append(
                {
                    "artist": row["artist"],
                    "title": row["title"],
                    "loop_path": row["loop_path"],
                    "song_id": row.get("song_id", ""),
                    "notes": row.get("notes", ""),
                }
            )

    logger.info(f"Loaded {len(mappings)} mappings from CSV")
    return mappings


def scan_directory_mappings(directory: str) -> List[Dict[str, Any]]:
    """Scan directory for MP4 files and create mappings.

    Attempts to parse artist and title from filename.
    Supported formats:
    - artist_-_title.mp4
    - artist - title.mp4
    - track_123_loop.mp4 (uses song_id)

    Args:
        directory: Path to directory containing loop files

    Returns:
        List of mapping dictionaries
    """
    logger.info(f"Scanning directory: {directory}")
    mappings = []

    for file_path in Path(directory).rglob("*.mp4"):
        filename = file_path.stem  # Without extension
        abs_path = str(file_path.absolute())

        # Try to parse artist and title from filename
        if "_-_" in filename:
            # Format: artist_-_title
            parts = filename.split("_-_", 1)
            artist = parts[0].replace("_", " ").title()
            title = parts[1].replace("_", " ").title()
        elif " - " in filename:
            # Format: artist - title
            parts = filename.split(" - ", 1)
            artist = parts[0].strip().title()
            title = parts[1].strip().title()
        elif filename.startswith("track_") and "_loop" in filename:
            # Format: track_123_loop
            song_id = filename.split("_")[1]
            artist = f"Song {song_id}"
            title = "Unknown Title"
            mappings.append(
                {
                    "artist": artist,
                    "title": title,
                    "loop_path": abs_path,
                    "song_id": song_id,
                    "notes": f"Auto-scanned from {file_path.name}",
                }
            )
            continue
        else:
            # Unknown format, use filename as title
            artist = "Unknown Artist"
            title = filename.replace("_", " ").title()

        mappings.append(
            {
                "artist": artist,
                "title": title,
                "loop_path": abs_path,
                "song_id": "",
                "notes": f"Auto-scanned from {file_path.name}",
            }
        )

    logger.info(f"Found {len(mappings)} MP4 files")
    return mappings


def import_mappings(
    mapper: TrackMapper,
    mappings: List[Dict[str, Any]],
    update_existing: bool = False,
    dry_run: bool = False,
) -> Dict[str, int]:
    """Import mappings into database.

    Args:
        mapper: TrackMapper instance
        mappings: List of mapping dictionaries
        update_existing: Update existing mappings (default: False)
        dry_run: Don't actually import, just show what would be done

    Returns:
        Dictionary with counts: added, updated, skipped, errors
    """
    stats = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}

    for i, mapping in enumerate(mappings, 1):
        artist = mapping.get("artist", "").strip()
        title = mapping.get("title", "").strip()
        loop_path = mapping.get("loop_path", "").strip()
        song_id = mapping.get("song_id", "").strip() or None
        notes = mapping.get("notes", "").strip() or None

        if not artist or not title or not loop_path:
            logger.warning(f"Skipping invalid mapping {i}: missing required fields")
            stats["errors"] += 1
            continue

        track_key = TrackMapper.normalize_track_key(artist, title)

        if dry_run:
            logger.info(f"[DRY RUN] Would add: {track_key} -> {loop_path}")
            stats["added"] += 1
            continue

        try:
            # Check if file exists
            if not os.path.isfile(loop_path):
                logger.warning(f"File not found: {loop_path}")
                stats["errors"] += 1
                continue

            # Try to add
            added = mapper.add_mapping(track_key, loop_path, song_id, notes)

            if added:
                logger.info(f"Added: {track_key} -> {loop_path}")
                stats["added"] += 1
            elif update_existing:
                # Try to update
                updated = mapper.update_mapping(track_key, loop_path, song_id, notes)
                if updated:
                    logger.info(f"Updated: {track_key} -> {loop_path}")
                    stats["updated"] += 1
                else:
                    logger.warning(f"Failed to update: {track_key}")
                    stats["errors"] += 1
            else:
                logger.info(f"Skipped (exists): {track_key}")
                stats["skipped"] += 1

        except Exception as e:
            logger.error(f"Error importing {track_key}: {e}")
            stats["errors"] += 1

    return stats


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Bulk import track-to-loop mappings")

    # Input source (mutually exclusive)
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--json", help="Import from JSON file")
    source_group.add_argument("--csv", help="Import from CSV file")
    source_group.add_argument("--scan", help="Scan directory for MP4 files")

    # Options
    parser.add_argument(
        "--update", action="store_true", help="Update existing mappings (default: skip)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be imported without actually importing",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Load mappings from source
        if args.json:
            mappings = load_json_mappings(args.json)
        elif args.csv:
            mappings = load_csv_mappings(args.csv)
        elif args.scan:
            mappings = scan_directory_mappings(args.scan)
        else:
            logger.error("No input source specified")
            return 1

        if not mappings:
            logger.warning("No mappings to import")
            return 0

        # Initialize mapper
        config = TrackMapperConfig.from_env()

        if args.dry_run:
            logger.info("DRY RUN MODE - No changes will be made")
        else:
            logger.info(f"Connecting to database: {config.postgres_db}")

        with TrackMapper(config) as mapper:
            # Import mappings
            stats = import_mappings(
                mapper, mappings, update_existing=args.update, dry_run=args.dry_run
            )

            # Print summary
            logger.info("")
            logger.info("=" * 60)
            logger.info("IMPORT SUMMARY")
            logger.info("=" * 60)
            logger.info(f"Total mappings: {len(mappings)}")
            logger.info(f"Added: {stats['added']}")
            logger.info(f"Updated: {stats['updated']}")
            logger.info(f"Skipped: {stats['skipped']}")
            logger.info(f"Errors: {stats['errors']}")
            logger.info("=" * 60)

            if args.dry_run:
                logger.info("DRY RUN - No changes were made")

            return 0 if stats["errors"] == 0 else 1

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
