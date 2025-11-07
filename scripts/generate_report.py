#!/usr/bin/env python3
"""Generate weekly analytics report.

This script generates a comprehensive weekly analytics report in text and HTML formats.
It can also send the report via Discord/Slack webhooks if configured.

Usage:
    python scripts/generate_report.py [OPTIONS]

Options:
    --days DAYS          Number of days for report (default: 7)
    --format FORMAT      Output format: text, html, both (default: both)
    --output-dir DIR     Output directory (default: ./reports)
    --send-notification  Send report via Discord/Slack webhook
    --webhook-url URL    Custom webhook URL for notifications

Examples:
    # Generate weekly report
    python scripts/generate_report.py

    # Generate 30-day report
    python scripts/generate_report.py --days 30

    # Generate and send notification
    python scripts/generate_report.py --send-notification
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from logging_module import LoggingConfig, Analytics


def format_duration(hours: float) -> str:
    """Format duration in hours to human-readable string.

    Args:
        hours: Duration in hours

    Returns:
        Formatted string (e.g., "2h 30m")
    """
    h = int(hours)
    m = int((hours - h) * 60)
    return f"{h}h {m}m"


def generate_text_report(
    analytics: Analytics,
    start_date: datetime,
    end_date: datetime
) -> str:
    """Generate text format report.

    Args:
        analytics: Analytics instance
        start_date: Report start date
        end_date: Report end date

    Returns:
        Report text
    """
    # Get statistics
    stats = analytics.get_play_stats(start_date=start_date, end_date=end_date)
    most_played = analytics.get_most_played_tracks(
        start_date=start_date,
        end_date=end_date,
        limit=10
    )
    error_summary = analytics.get_error_summary(
        start_date=start_date,
        end_date=end_date
    )
    uptime_by_day = analytics.get_uptime_by_day(
        start_date=start_date,
        end_date=end_date
    )

    # Build report
    lines = []
    lines.append("=" * 80)
    lines.append("24/7 RADIO STREAM - ANALYTICS REPORT")
    lines.append("=" * 80)
    lines.append(f"Period: {start_date.date()} to {end_date.date()}")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 80)
    lines.append("")

    # Overall statistics
    lines.append("OVERALL STATISTICS")
    lines.append("-" * 80)
    lines.append(f"  Total Plays:        {stats['total_plays']:,}")
    lines.append(f"  Unique Tracks:      {stats['unique_tracks']:,}")
    lines.append(f"  Total Duration:     {format_duration(stats['total_duration_hours'])}")
    lines.append(f"  Avg Track Duration: {stats['avg_duration_seconds']:.1f} seconds")
    lines.append(f"  Error Rate:         {stats['error_rate']:.2f}%")
    lines.append(f"  Uptime:             {stats['uptime_percent']:.2f}%")
    lines.append("")

    # Most played tracks
    lines.append("TOP 10 MOST PLAYED TRACKS")
    lines.append("-" * 80)
    lines.append(f"{'Rank':<6} {'Plays':<8} {'Artist - Title'}")
    lines.append("-" * 80)
    for i, track in enumerate(most_played, 1):
        artist_title = f"{track['artist']} - {track['title']}"
        if len(artist_title) > 60:
            artist_title = artist_title[:57] + "..."
        lines.append(f"{i:<6} {track['play_count']:<8} {artist_title}")
    lines.append("")

    # Error summary
    if error_summary:
        lines.append("ERROR SUMMARY")
        lines.append("-" * 80)
        lines.append(f"{'Service':<15} {'Severity':<12} {'Total':<8} {'Resolved':<10} {'Unresolved'}")
        lines.append("-" * 80)
        for error in error_summary:
            lines.append(
                f"{error['service']:<15} "
                f"{error['severity']:<12} "
                f"{error['error_count']:<8} "
                f"{error['resolved_count']:<10} "
                f"{error['unresolved_count']}"
            )
        lines.append("")

    # Daily uptime
    if uptime_by_day:
        lines.append("DAILY UPTIME")
        lines.append("-" * 80)
        lines.append(f"{'Date':<12} {'Plays':<8} {'Duration':<12} {'Uptime'}")
        lines.append("-" * 80)
        for day in uptime_by_day:
            lines.append(
                f"{day['date']:<12} "
                f"{day['total_plays']:<8} "
                f"{format_duration(day['total_hours']):<12} "
                f"{day['uptime_percent']:.2f}%"
            )
        lines.append("")

    lines.append("=" * 80)
    lines.append("END OF REPORT")
    lines.append("=" * 80)

    return "\n".join(lines)


def generate_html_report(
    analytics: Analytics,
    start_date: datetime,
    end_date: datetime
) -> str:
    """Generate HTML format report.

    Args:
        analytics: Analytics instance
        start_date: Report start date
        end_date: Report end date

    Returns:
        Report HTML
    """
    # Get statistics
    stats = analytics.get_play_stats(start_date=start_date, end_date=end_date)
    most_played = analytics.get_most_played_tracks(
        start_date=start_date,
        end_date=end_date,
        limit=10
    )
    error_summary = analytics.get_error_summary(
        start_date=start_date,
        end_date=end_date
    )
    uptime_by_day = analytics.get_uptime_by_day(
        start_date=start_date,
        end_date=end_date
    )

    # Determine status color
    if stats['uptime_percent'] >= 99:
        status_color = "#27ae60"  # Green
        status_text = "Excellent"
    elif stats['uptime_percent'] >= 95:
        status_color = "#f39c12"  # Orange
        status_text = "Good"
    else:
        status_color = "#e74c3c"  # Red
        status_text = "Needs Attention"

    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>24/7 Radio Stream - Analytics Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
            color: #333;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2em;
        }}
        .header .period {{
            margin-top: 10px;
            opacity: 0.9;
        }}
        .status-badge {{
            display: inline-block;
            background: {status_color};
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            margin-top: 10px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .stat-card .label {{
            color: #666;
            font-size: 0.9em;
            margin-bottom: 5px;
        }}
        .stat-card .value {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }}
        .stat-card .value.uptime {{
            color: {status_color};
        }}
        .section {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .section h2 {{
            margin-top: 0;
            color: #667eea;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th {{
            background: #f8f9fa;
            text-align: left;
            padding: 12px;
            font-weight: 600;
            color: #666;
        }}
        td {{
            padding: 12px;
            border-bottom: 1px solid #eee;
        }}
        tr:hover {{
            background: #f8f9fa;
        }}
        .footer {{
            text-align: center;
            color: #666;
            margin-top: 30px;
            padding: 20px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📻 24/7 Radio Stream Analytics</h1>
        <div class="period">
            {start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}
        </div>
        <div class="status-badge">{status_text}</div>
    </div>

    <div class="stats-grid">
        <div class="stat-card">
            <div class="label">Total Plays</div>
            <div class="value">{stats['total_plays']:,}</div>
        </div>
        <div class="stat-card">
            <div class="label">Unique Tracks</div>
            <div class="value">{stats['unique_tracks']:,}</div>
        </div>
        <div class="stat-card">
            <div class="label">Total Duration</div>
            <div class="value">{format_duration(stats['total_duration_hours'])}</div>
        </div>
        <div class="stat-card">
            <div class="label">Uptime</div>
            <div class="value uptime">{stats['uptime_percent']:.2f}%</div>
        </div>
    </div>

    <div class="section">
        <h2>🎵 Top 10 Most Played Tracks</h2>
        <table>
            <thead>
                <tr>
                    <th style="width: 50px;">#</th>
                    <th>Artist</th>
                    <th>Title</th>
                    <th style="width: 100px;">Plays</th>
                    <th style="width: 120px;">Total Time</th>
                </tr>
            </thead>
            <tbody>
    """

    for i, track in enumerate(most_played, 1):
        html += f"""
                <tr>
                    <td>{i}</td>
                    <td>{track['artist']}</td>
                    <td>{track['title']}</td>
                    <td>{track['play_count']}</td>
                    <td>{format_duration(track['total_duration_hours'])}</td>
                </tr>
        """

    html += """
            </tbody>
        </table>
    </div>
    """

    if error_summary:
        html += """
    <div class="section">
        <h2>⚠️ Error Summary</h2>
        <table>
            <thead>
                <tr>
                    <th>Service</th>
                    <th>Severity</th>
                    <th>Total</th>
                    <th>Resolved</th>
                    <th>Unresolved</th>
                </tr>
            </thead>
            <tbody>
        """

        for error in error_summary:
            html += f"""
                <tr>
                    <td>{error['service']}</td>
                    <td>{error['severity']}</td>
                    <td>{error['error_count']}</td>
                    <td>{error['resolved_count']}</td>
                    <td>{error['unresolved_count']}</td>
                </tr>
            """

        html += """
            </tbody>
        </table>
    </div>
        """

    if uptime_by_day:
        html += """
    <div class="section">
        <h2>📊 Daily Uptime</h2>
        <table>
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Plays</th>
                    <th>Duration</th>
                    <th>Uptime</th>
                </tr>
            </thead>
            <tbody>
        """

        for day in uptime_by_day:
            html += f"""
                <tr>
                    <td>{day['date']}</td>
                    <td>{day['total_plays']}</td>
                    <td>{format_duration(day['total_hours'])}</td>
                    <td>{day['uptime_percent']:.2f}%</td>
                </tr>
            """

        html += """
            </tbody>
        </table>
    </div>
        """

    html += f"""
    <div class="footer">
        Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </div>
</body>
</html>
    """

    return html


def send_discord_notification(webhook_url: str, stats: Dict[str, Any]) -> bool:
    """Send report summary to Discord webhook.

    Args:
        webhook_url: Discord webhook URL
        stats: Statistics dictionary

    Returns:
        True if sent successfully, False otherwise
    """
    try:
        import requests

        # Determine color based on uptime
        if stats['uptime_percent'] >= 99:
            color = 0x27ae60  # Green
        elif stats['uptime_percent'] >= 95:
            color = 0xf39c12  # Orange
        else:
            color = 0xe74c3c  # Red

        embed = {
            "title": "📊 Weekly Radio Stream Report",
            "description": f"Analytics for {stats['start_date']} to {stats['end_date']}",
            "color": color,
            "fields": [
                {
                    "name": "Total Plays",
                    "value": f"{stats['total_plays']:,}",
                    "inline": True
                },
                {
                    "name": "Unique Tracks",
                    "value": f"{stats['unique_tracks']:,}",
                    "inline": True
                },
                {
                    "name": "Total Duration",
                    "value": format_duration(stats['total_duration_hours']),
                    "inline": True
                },
                {
                    "name": "Uptime",
                    "value": f"{stats['uptime_percent']:.2f}%",
                    "inline": True
                },
                {
                    "name": "Error Rate",
                    "value": f"{stats['error_rate']:.2f}%",
                    "inline": True
                },
                {
                    "name": "Avg Duration",
                    "value": f"{stats['avg_duration_seconds']:.1f}s",
                    "inline": True
                }
            ],
            "timestamp": datetime.now().isoformat()
        }

        payload = {"embeds": [embed]}

        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        return True

    except Exception as e:
        print(f"Failed to send Discord notification: {e}", file=sys.stderr)
        return False


def main():
    """Main entry point for report generation."""
    parser = argparse.ArgumentParser(
        description='Generate weekly analytics report',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='Number of days for report (default: 7)'
    )
    parser.add_argument(
        '--format',
        type=str,
        choices=['text', 'html', 'both'],
        default='both',
        help='Output format (default: both)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='./reports',
        help='Output directory (default: ./reports)'
    )
    parser.add_argument(
        '--send-notification',
        action='store_true',
        help='Send report via Discord/Slack webhook'
    )
    parser.add_argument(
        '--webhook-url',
        type=str,
        help='Custom webhook URL for notifications'
    )

    args = parser.parse_args()

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=args.days)

    print(f"\n{'='*60}")
    print(f"Generating {args.days}-day Analytics Report")
    print(f"{'='*60}\n")

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    try:
        # Initialize analytics
        config = LoggingConfig.from_env()
        config.validate()
        analytics = Analytics(config)

        # Generate timestamp for filenames
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Generate text report
        if args.format in ['text', 'both']:
            print("Generating text report...")
            text_report = generate_text_report(analytics, start_date, end_date)
            text_file = os.path.join(
                args.output_dir,
                f'weekly_report_{timestamp}.txt'
            )
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(text_report)
            print(f"  ✓ Saved to {text_file}")

        # Generate HTML report
        if args.format in ['html', 'both']:
            print("Generating HTML report...")
            html_report = generate_html_report(analytics, start_date, end_date)
            html_file = os.path.join(
                args.output_dir,
                f'weekly_report_{timestamp}.html'
            )
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_report)
            print(f"  ✓ Saved to {html_file}")

        # Send notification if requested
        if args.send_notification:
            webhook_url = args.webhook_url or os.getenv('DISCORD_WEBHOOK_URL')
            if webhook_url:
                print("Sending Discord notification...")
                stats = analytics.get_play_stats(
                    start_date=start_date,
                    end_date=end_date
                )
                if send_discord_notification(webhook_url, stats):
                    print("  ✓ Notification sent successfully")
                else:
                    print("  ✗ Failed to send notification")
            else:
                print("  ⚠ No webhook URL configured (use --webhook-url or DISCORD_WEBHOOK_URL)")

        analytics.close()

        print(f"\n{'='*60}")
        print(f"✓ Report generation completed!")
        print(f"{'='*60}\n")

        return 0

    except Exception as e:
        print(f"\n✗ Error generating report: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())



