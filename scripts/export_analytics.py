#!/usr/bin/env python3
"""Export analytics data to CSV files.

This script exports play history and analytics data to CSV format
for external analysis and reporting.

Usage:
    python scripts/export_analytics.py [OPTIONS]

Options:
    --days DAYS          Number of days to export (default: 30)
    --output-dir DIR     Output directory for CSV files (default: ./analytics_export)
    --include-errors     Include error log export
    --include-metrics    Include system metrics export

Examples:
    # Export last 7 days
    python scripts/export_analytics.py --days 7

    # Export with errors and metrics
    python scripts/export_analytics.py --days 30 --include-errors --include-metrics

    # Custom output directory
    python scripts/export_analytics.py --output-dir /tmp/reports
"""

import argparse
import csv
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from logging_module import LoggingConfig, Analytics
from sqlalchemy import create_engine, text


def export_play_history(engine, start_date: datetime, end_date: datetime, output_file: str) -> int:
    """Export play history to CSV.

    Args:
        engine: SQLAlchemy engine
        start_date: Start date for export
        end_date: End date for export
        output_file: Path to output CSV file

    Returns:
        Number of records exported
    """
    print(f"Exporting play history to {output_file}...")

    with engine.connect() as conn:
        result = conn.execute(
            text(
                """
                SELECT
                    id, track_key, artist, title, album,
                    azuracast_song_id, loop_file_path,
                    started_at, ended_at, duration_seconds,
                    expected_duration_seconds, ffmpeg_pid,
                    had_errors, error_message, error_count
                FROM play_history
                WHERE started_at >= :start_date AND started_at <= :end_date
                ORDER BY started_at DESC
            """
            ),
            {"start_date": start_date, "end_date": end_date},
        )

        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "ID",
                    "Track Key",
                    "Artist",
                    "Title",
                    "Album",
                    "AzuraCast Song ID",
                    "Loop File Path",
                    "Started At",
                    "Ended At",
                    "Duration (seconds)",
                    "Expected Duration (seconds)",
                    "FFmpeg PID",
                    "Had Errors",
                    "Error Message",
                    "Error Count",
                ]
            )

            count = 0
            for row in result:
                writer.writerow(
                    [
                        row[0],  # id
                        row[1],  # track_key
                        row[2],  # artist
                        row[3],  # title
                        row[4],  # album
                        row[5],  # azuracast_song_id
                        row[6],  # loop_file_path
                        row[7].isoformat() if row[7] else None,  # started_at
                        row[8].isoformat() if row[8] else None,  # ended_at
                        row[9],  # duration_seconds
                        row[10],  # expected_duration_seconds
                        row[11],  # ffmpeg_pid
                        row[12],  # had_errors
                        row[13],  # error_message
                        row[14],  # error_count
                    ]
                )
                count += 1

    print(f"  ✓ Exported {count} play history records")
    return count


def export_error_log(engine, start_date: datetime, end_date: datetime, output_file: str) -> int:
    """Export error log to CSV.

    Args:
        engine: SQLAlchemy engine
        start_date: Start date for export
        end_date: End date for export
        output_file: Path to output CSV file

    Returns:
        Number of records exported
    """
    print(f"Exporting error log to {output_file}...")

    with engine.connect() as conn:
        result = conn.execute(
            text(
                """
                SELECT
                    id, timestamp, service, severity,
                    message, resolved, resolved_at,
                    play_history_id
                FROM error_log
                WHERE timestamp >= :start_date AND timestamp <= :end_date
                ORDER BY timestamp DESC
            """
            ),
            {"start_date": start_date, "end_date": end_date},
        )

        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "ID",
                    "Timestamp",
                    "Service",
                    "Severity",
                    "Message",
                    "Resolved",
                    "Resolved At",
                    "Play History ID",
                ]
            )

            count = 0
            for row in result:
                writer.writerow(
                    [
                        row[0],  # id
                        row[1].isoformat() if row[1] else None,  # timestamp
                        row[2],  # service
                        row[3],  # severity
                        row[4],  # message
                        row[5],  # resolved
                        row[6].isoformat() if row[6] else None,  # resolved_at
                        row[7],  # play_history_id
                    ]
                )
                count += 1

    print(f"  ✓ Exported {count} error log records")
    return count


def export_system_metrics(
    engine, start_date: datetime, end_date: datetime, output_file: str
) -> int:
    """Export system metrics to CSV.

    Args:
        engine: SQLAlchemy engine
        start_date: Start date for export
        end_date: End date for export
        output_file: Path to output CSV file

    Returns:
        Number of records exported
    """
    print(f"Exporting system metrics to {output_file}...")

    with engine.connect() as conn:
        result = conn.execute(
            text(
                """
                SELECT
                    id, timestamp, metric_name, metric_value,
                    unit, service
                FROM system_metrics
                WHERE timestamp >= :start_date AND timestamp <= :end_date
                ORDER BY timestamp DESC
            """
            ),
            {"start_date": start_date, "end_date": end_date},
        )

        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Timestamp", "Metric Name", "Metric Value", "Unit", "Service"])

            count = 0
            for row in result:
                writer.writerow(
                    [
                        row[0],  # id
                        row[1].isoformat() if row[1] else None,  # timestamp
                        row[2],  # metric_name
                        row[3],  # metric_value
                        row[4],  # unit
                        row[5],  # service
                    ]
                )
                count += 1

    print(f"  ✓ Exported {count} system metric records")
    return count


def export_analytics_summary(
    analytics: Analytics, start_date: datetime, end_date: datetime, output_file: str
) -> None:
    """Export analytics summary to CSV.

    Args:
        analytics: Analytics instance
        start_date: Start date for export
        end_date: End date for export
        output_file: Path to output CSV file
    """
    print(f"Exporting analytics summary to {output_file}...")

    # Get overall stats
    stats = analytics.get_play_stats(start_date=start_date, end_date=end_date)

    # Get most played tracks
    most_played = analytics.get_most_played_tracks(
        start_date=start_date, end_date=end_date, limit=50
    )

    # Get error summary
    error_summary = analytics.get_error_summary(start_date=start_date, end_date=end_date)

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Write overall stats
        writer.writerow(["OVERALL STATISTICS"])
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Total Plays", stats["total_plays"]])
        writer.writerow(["Unique Tracks", stats["unique_tracks"]])
        writer.writerow(["Total Duration (hours)", f"{stats['total_duration_hours']:.2f}"])
        writer.writerow(["Avg Duration (seconds)", f"{stats['avg_duration_seconds']:.2f}"])
        writer.writerow(["Error Rate (%)", f"{stats['error_rate']:.2f}"])
        writer.writerow(["Uptime (%)", f"{stats['uptime_percent']:.2f}"])
        writer.writerow([])

        # Write most played tracks
        writer.writerow(["MOST PLAYED TRACKS"])
        writer.writerow(["Rank", "Artist", "Title", "Play Count", "Total Hours", "Error Count"])
        for i, track in enumerate(most_played, 1):
            writer.writerow(
                [
                    i,
                    track["artist"],
                    track["title"],
                    track["play_count"],
                    f"{track['total_duration_hours']:.2f}",
                    track["error_count"],
                ]
            )
        writer.writerow([])

        # Write error summary
        writer.writerow(["ERROR SUMMARY"])
        writer.writerow(["Service", "Severity", "Total", "Resolved", "Unresolved"])
        for error in error_summary:
            writer.writerow(
                [
                    error["service"],
                    error["severity"],
                    error["error_count"],
                    error["resolved_count"],
                    error["unresolved_count"],
                ]
            )

    print(f"  ✓ Exported analytics summary")


def main():
    """Main entry point for export script."""
    parser = argparse.ArgumentParser(
        description="Export analytics data to CSV files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export last 7 days
  python scripts/export_analytics.py --days 7

  # Export with errors and metrics
  python scripts/export_analytics.py --days 30 --include-errors --include-metrics

  # Custom output directory
  python scripts/export_analytics.py --output-dir /tmp/reports
        """,
    )

    parser.add_argument(
        "--days", type=int, default=30, help="Number of days to export (default: 30)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./analytics_export",
        help="Output directory for CSV files (default: ./analytics_export)",
    )
    parser.add_argument("--include-errors", action="store_true", help="Include error log export")
    parser.add_argument(
        "--include-metrics", action="store_true", help="Include system metrics export"
    )

    args = parser.parse_args()

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=args.days)

    print(f"\n{'='*60}")
    print(f"Analytics Export")
    print(f"{'='*60}")
    print(f"Date range: {start_date.date()} to {end_date.date()}")
    print(f"Output directory: {args.output_dir}")
    print(f"{'='*60}\n")

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Create timestamp for filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
        # Initialize configuration and analytics
        config = LoggingConfig.from_env()
        config.validate()
        analytics = Analytics(config)
        engine = analytics.engine

        # Export play history
        play_history_file = os.path.join(args.output_dir, f"play_history_{timestamp}.csv")
        export_play_history(engine, start_date, end_date, play_history_file)

        # Export analytics summary
        summary_file = os.path.join(args.output_dir, f"analytics_summary_{timestamp}.csv")
        export_analytics_summary(analytics, start_date, end_date, summary_file)

        # Export error log if requested
        if args.include_errors:
            error_log_file = os.path.join(args.output_dir, f"error_log_{timestamp}.csv")
            export_error_log(engine, start_date, end_date, error_log_file)

        # Export system metrics if requested
        if args.include_metrics:
            metrics_file = os.path.join(args.output_dir, f"system_metrics_{timestamp}.csv")
            export_system_metrics(engine, start_date, end_date, metrics_file)

        analytics.close()

        print(f"\n{'='*60}")
        print(f"✓ Export completed successfully!")
        print(f"{'='*60}\n")

        return 0

    except Exception as e:
        print(f"\n✗ Error during export: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
