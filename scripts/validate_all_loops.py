#!/usr/bin/env python3
"""
Batch validation script for all video loop files.

This script scans a directory for MP4 files and validates each one,
generating a detailed report of validation results.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from asset_manager.manager import AssetManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def validate_directory(
    directory: str,
    output_file: Optional[str] = None,
    verbose: bool = False,
) -> bool:
    """
    Validate all loop files in a directory.

    Args:
        directory: Directory to scan for MP4 files
        output_file: Optional JSON file to write results
        verbose: Whether to show detailed output

    Returns:
        True if all loops are valid, False otherwise
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info(f"Validating loops in: {directory}")

    # Initialize asset manager
    manager = AssetManager()

    # Validate all loops
    results = manager.validate_all_loops_in_directory(directory)

    # Print summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Total files:   {results['total']}")
    print(f"Valid:         {results['valid']}")
    print(f"Invalid:       {results['invalid']}")
    print(f"Success rate:  {results['valid']/results['total']*100:.1f}%")
    print("=" * 60)

    # Print errors if any
    if results["errors"]:
        print("\nERRORS:")
        print("-" * 60)
        for error in results["errors"]:
            print(f"\nFile: {error['file']}")
            for err in error["errors"]:
                print(f"  - {err}")
        print("-" * 60)

    # Write to JSON if requested
    if output_file:
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results written to: {output_file}")

    # Return success status
    return results["invalid"] == 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Validate all video loop files in a directory")
    parser.add_argument(
        "directory",
        nargs="?",
        help="Directory to scan (default: /srv/loops/tracks)",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output JSON file for results",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--default-loop",
        action="store_true",
        help="Validate only the default loop",
    )

    args = parser.parse_args()

    # Handle default loop validation
    if args.default_loop:
        manager = AssetManager()
        if manager.ensure_default_loop_exists():
            print("✓ Default loop is valid")
            return 0
        else:
            print("✗ Default loop is invalid or missing")
            return 1

    # Validate directory
    directory = args.directory or "/srv/loops/tracks"

    try:
        success = validate_directory(directory, args.output, args.verbose)
        return 0 if success else 1
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
