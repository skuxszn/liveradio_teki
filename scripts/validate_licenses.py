#!/usr/bin/env python3
"""
License compliance validation script.

This script validates the license manifest and checks compliance
for all played tracks. It can also generate compliance reports.

Usage:
    python scripts/validate_licenses.py
    python scripts/validate_licenses.py --manifest /path/to/manifest.json
    python scripts/validate_licenses.py --check-played
    python scripts/validate_licenses.py --export report.csv
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List

# Add parent directory to path for imports  # noqa: E402
sys.path.insert(0, str(Path(__file__).parent.parent))

from security.license_manager import (  # noqa: E402
    LicenseManager,
    LicenseManifestError,
)


def get_played_tracks_from_db() -> List[str]:
    """Get list of played track IDs from database.

    Returns:
        List of unique track IDs that have been played

    Note:
        This is a placeholder implementation. In production, this would
        query the play_history table from the database.
    """
    # TODO: Implement actual database query
    # For now, return empty list
    return []


def validate_manifest(manifest_path: str) -> bool:
    """Validate license manifest structure and content.

    Args:
        manifest_path: Path to license manifest file

    Returns:
        True if manifest is valid, False otherwise
    """
    print(f"Validating license manifest: {manifest_path}")
    print("=" * 70)

    try:
        manager = LicenseManager(manifest_path)

        # Check if manifest exists and loaded successfully
        total_licenses = len(manager.licenses)

        if total_licenses == 0:
            print("⚠️  WARNING: License manifest is empty")
            print()
            print("No track licenses found. This means:")
            print("  1. No tracks have been licensed yet, OR")
            print("  2. The manifest file is missing or invalid")
            print()
            return True  # Empty is valid, just a warning

        print("✓ Manifest loaded successfully")
        print(f"✓ Found {total_licenses} track licenses")
        print()

        # Validate each license
        invalid_count = 0
        for track_id, license_info in manager.licenses.items():
            issues = []

            if not license_info.license:
                issues.append("missing license type")
            if not license_info.license_url:
                issues.append("missing license URL")
            if not license_info.artist:
                issues.append("missing artist")
            if not license_info.title:
                issues.append("missing title")

            if issues:
                invalid_count += 1
                print(f"⚠️  Track {track_id}: {', '.join(issues)}")

        if invalid_count > 0:
            print()
            print(f"Found {invalid_count} tracks with incomplete license information")
            return False
        else:
            print("✓ All licenses have complete information")
            print()

        # Show license type breakdown
        license_types = {}
        for license_info in manager.licenses.values():
            license_type = license_info.license
            license_types[license_type] = license_types.get(license_type, 0) + 1

        print("License Type Distribution:")
        for license_type, count in sorted(license_types.items(), key=lambda x: x[1], reverse=True):
            print(f"  {license_type}: {count} tracks")

        print()
        print("=" * 70)
        print("✓ Manifest validation PASSED")
        return True

    except LicenseManifestError as e:
        print(f"❌ ERROR: {e}")
        print()
        print("=" * 70)
        print("✗ Manifest validation FAILED")
        return False
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
        print()
        print("=" * 70)
        print("✗ Manifest validation FAILED")
        return False


def check_played_compliance(manifest_path: str) -> bool:
    """Check license compliance for all played tracks.

    Args:
        manifest_path: Path to license manifest file

    Returns:
        True if all played tracks are licensed, False otherwise
    """
    print("Checking license compliance for played tracks...")
    print("=" * 70)

    try:
        manager = LicenseManager(manifest_path)

        # Get played tracks (from database or other source)
        played_tracks = get_played_tracks_from_db()

        if not played_tracks:
            print("⚠️  No played track data found")
            print()
            print("Unable to check compliance - no play history available.")
            print("This could mean:")
            print("  1. No tracks have been played yet")
            print("  2. Database is not accessible")
            print("  3. Play history tracking is not enabled")
            return True

        # Generate compliance report
        report = manager.generate_compliance_report(played_tracks)

        print(f"Total tracks played: {report['total_tracks_played']}")
        print(f"Licensed tracks: {report['licensed_tracks']}")
        print(f"Unlicensed tracks: {report['unlicensed_tracks']}")
        print(f"Compliance rate: {report['compliance_rate']}%")
        print()

        if report["unlicensed_tracks"] > 0:
            print("⚠️  Unlicensed tracks found:")
            for track_id in report["unlicensed_track_ids"][:10]:  # Show first 10
                print(f"  - {track_id}")
            if len(report["unlicensed_track_ids"]) > 10:
                print(f"  ... and {len(report['unlicensed_track_ids']) - 10} more")
            print()
            print("=" * 70)
            print("✗ Compliance check FAILED - unlicensed tracks detected")
            return False
        else:
            print("✓ All played tracks have valid licenses")
            print()
            print("=" * 70)
            print("✓ Compliance check PASSED")
            return True

    except Exception as e:
        print(f"❌ ERROR: {e}")
        print()
        print("=" * 70)
        print("✗ Compliance check FAILED")
        return False


def export_report(manifest_path: str, output_path: str, format: str = "csv") -> bool:
    """Export license manifest to a report file.

    Args:
        manifest_path: Path to license manifest file
        output_path: Path to output report file
        format: Export format ('csv' or 'json')

    Returns:
        True if export successful, False otherwise
    """
    print(f"Exporting license report to: {output_path}")
    print("=" * 70)

    try:
        manager = LicenseManager(manifest_path)

        if format == "csv":
            manager.export_to_csv(output_path)
        elif format == "json":
            # Export as JSON
            with open(output_path, "w", encoding="utf-8") as f:
                data = {
                    "generated_at": datetime.utcnow().isoformat(),
                    "total_tracks": len(manager.licenses),
                    "tracks": [
                        license_info.to_dict() for license_info in manager.licenses.values()
                    ],
                }
                json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"✓ Exported {len(manager.licenses)} licenses to {output_path}")
        print()
        print("=" * 70)
        return True

    except Exception as e:
        print(f"❌ ERROR: {e}")
        print()
        print("=" * 70)
        print("✗ Export FAILED")
        return False


def main():
    """Main entry point for license validation script."""
    parser = argparse.ArgumentParser(
        description="Validate license manifest and check compliance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate manifest structure
  python scripts/validate_licenses.py

  # Check compliance for played tracks
  python scripts/validate_licenses.py --check-played

  # Export manifest to CSV
  python scripts/validate_licenses.py --export licenses.csv

  # Export manifest to JSON
  python scripts/validate_licenses.py --export report.json --format json

  # Use custom manifest path
  python scripts/validate_licenses.py \\
      --manifest /path/to/manifest.json
        """,
    )

    parser.add_argument(
        "--manifest",
        type=str,
        default=None,
        help=(
            "Path to license manifest file "
            "(default: from env or /srv/config/license_manifest.json)"
        ),
    )

    parser.add_argument(
        "--check-played",
        action="store_true",
        help="Check compliance for all played tracks",
    )

    parser.add_argument(
        "--export",
        type=str,
        default=None,
        help="Export manifest to file (CSV or JSON)",
    )

    parser.add_argument(
        "--format",
        choices=["csv", "json"],
        default=None,
        help="Export format (auto-detected from filename if not specified)",
    )

    args = parser.parse_args()

    # Determine manifest path
    if args.manifest:
        manifest_path = args.manifest
    else:
        manifest_path = os.getenv("LICENSE_MANIFEST_PATH", "/srv/config/license_manifest.json")

    print()
    print("LICENSE VALIDATION TOOL")
    print("=" * 70)
    print()

    # Perform requested operations
    success = True

    if args.export:
        # Determine export format
        if args.format:
            export_format = args.format
        else:
            # Auto-detect from filename
            if args.export.endswith(".json"):
                export_format = "json"
            else:
                export_format = "csv"

        success = export_report(manifest_path, args.export, export_format)

    elif args.check_played:
        success = check_played_compliance(manifest_path)

    else:
        # Default: validate manifest
        success = validate_manifest(manifest_path)

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
