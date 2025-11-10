"""Input validation utilities."""

import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse


def validate_url(url: str) -> bool:
    """Validate if string is a valid URL.

    Args:
        url: URL string to validate.

    Returns:
        bool: True if valid URL.
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def validate_path(path: str) -> bool:
    """Validate if string is a valid file path.

    Args:
        path: Path string to validate.

    Returns:
        bool: True if valid path format.
    """
    try:
        Path(path)
        return True
    except Exception:
        return False


def validate_resolution(resolution: str) -> Optional[tuple[int, int]]:
    """Validate and parse video resolution.

    Args:
        resolution: Resolution string (e.g., "1280:720").

    Returns:
        Optional[tuple[int, int]]: Width and height, or None if invalid.
    """
    pattern = r"^(\d+):(\d+)$"
    match = re.match(pattern, resolution)

    if not match:
        return None

    width, height = int(match.group(1)), int(match.group(2))

    if width <= 0 or height <= 0:
        return None

    return (width, height)


def validate_bitrate(bitrate: str) -> Optional[int]:
    """Validate and parse bitrate string.

    Args:
        bitrate: Bitrate string (e.g., "3000k" or "192k").

    Returns:
        Optional[int]: Bitrate in kbps, or None if invalid.
    """
    pattern = r"^(\d+)k$"
    match = re.match(pattern, bitrate.lower())

    if not match:
        return None

    return int(match.group(1))


def validate_email(email: str) -> bool:
    """Validate email address format.

    Args:
        email: Email address to validate.

    Returns:
        bool: True if valid email format.
    """
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_username(username: str) -> bool:
    """Validate username format.

    Args:
        username: Username to validate.

    Returns:
        bool: True if valid username.
    """
    # Alphanumeric, underscore, hyphen, 3-128 characters
    pattern = r"^[a-zA-Z0-9_-]{3,128}$"
    return bool(re.match(pattern, username))

