"""
Dynamic overlay generation for "Now Playing" displays.

This module generates PNG overlays with track information (artist, title)
that can be composited onto video loops using FFmpeg.
"""

import hashlib
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple, Union

from PIL import Image, ImageDraw, ImageFont
from PIL.ImageFont import FreeTypeFont

from asset_manager.config import AssetConfig, get_config

logger = logging.getLogger(__name__)


class OverlayGenerator:
    """Generator for dynamic video overlays."""

    def __init__(self, config: Optional[AssetConfig] = None):
        """
        Initialize the overlay generator.

        Args:
            config: Asset configuration. If None, uses default config.
        """
        self.config = config or get_config()
        self.logger = logging.getLogger(__name__)
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Ensure required directories exist."""
        Path(self.config.overlays_path).mkdir(parents=True, exist_ok=True)
        Path(self.config.templates_path).mkdir(parents=True, exist_ok=True)

    def generate_overlay(
        self,
        artist: str,
        title: str,
        template: Optional[str] = None,
        album: Optional[str] = None,
    ) -> str:
        """
        Generate a PNG overlay with track information.

        The overlay is cached based on a hash of the track information.
        If an overlay with the same content already exists and is fresh,
        it will be reused.

        Args:
            artist: Artist name
            title: Song title
            template: Optional template name (default: basic lower-third)
            album: Optional album name

        Returns:
            Absolute path to the generated overlay PNG

        Raises:
            RuntimeError: If overlay generation fails
        """
        # Generate cache key from track info
        cache_key = self._generate_cache_key(artist, title, album or "")
        overlay_path = os.path.join(self.config.overlays_path, f"{cache_key}.png")

        # Check if cached overlay exists and is fresh
        if self._is_overlay_fresh(overlay_path):
            self.logger.debug(f"Using cached overlay: {overlay_path}")
            return overlay_path

        # Generate new overlay
        try:
            if template:
                # Use template-based generation
                self._generate_from_template(artist, title, template, album, overlay_path)
            else:
                # Use basic text-based generation
                self._generate_basic_overlay(artist, title, album, overlay_path)

            self.logger.info(f"Generated overlay: {overlay_path}")
            return overlay_path
        except Exception as e:
            self.logger.error(f"Failed to generate overlay: {e}")
            raise RuntimeError(f"Overlay generation failed: {e}")

    def _generate_basic_overlay(
        self,
        artist: str,
        title: str,
        album: Optional[str],
        output_path: str,
    ) -> None:
        """
        Generate a basic lower-third overlay with text.

        Creates a semi-transparent black bar at the bottom with white text
        showing "Now Playing" information.

        Args:
            artist: Artist name
            title: Song title
            album: Optional album name
            output_path: Path where to save the overlay
        """
        # Get target resolution
        width = self.config.get_target_width()
        height = self.config.get_target_height()

        # Create transparent image
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Lower third dimensions (bottom 20% of screen)
        bar_height = int(height * 0.20)
        bar_y = height - bar_height

        # Draw semi-transparent black bar
        bg_color = self._hex_to_rgba(
            self.config.overlay_background_color, self.config.overlay_opacity
        )
        draw.rectangle([(0, bar_y), (width, height)], fill=bg_color)

        # Load font
        font_large: Union[FreeTypeFont, ImageFont.ImageFont]
        font_medium: Union[FreeTypeFont, ImageFont.ImageFont]
        font_small: Union[FreeTypeFont, ImageFont.ImageFont]

        try:
            # Try to load a system font
            font_large = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                self.config.overlay_font_size,
            )
            font_medium = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                int(self.config.overlay_font_size * 0.7),
            )
            font_small = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                int(self.config.overlay_font_size * 0.5),
            )
        except OSError:
            # Fallback to default font
            self.logger.warning("System fonts not found, using default")
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()

        text_color = self._hex_to_rgba(self.config.overlay_font_color, 255)

        # Calculate positions
        padding = 20
        y_pos = bar_y + padding

        # Draw "Now Playing" label
        label_text = "♪ NOW PLAYING"
        draw.text((padding, y_pos), label_text, fill=text_color, font=font_small)
        y_pos += int(self.config.overlay_font_size * 0.6)

        # Draw artist - title
        main_text = f"{artist} - {title}"
        # Truncate if too long
        max_width = width - (2 * padding)
        main_text = self._truncate_text(draw, main_text, font_large, max_width)
        draw.text((padding, y_pos), main_text, fill=text_color, font=font_large)
        y_pos += int(self.config.overlay_font_size * 1.2)

        # Draw album if provided
        if album:
            album_text = f"Album: {album}"
            album_text = self._truncate_text(draw, album_text, font_medium, max_width)
            draw.text((padding, y_pos), album_text, fill=text_color, font=font_medium)

        # Save image
        img.save(output_path, "PNG")

    def _generate_from_template(
        self,
        artist: str,
        title: str,
        template: str,
        album: Optional[str],
        output_path: str,
    ) -> None:
        """
        Generate overlay from a template image.

        Loads a template PNG and overlays text on top of it.

        Args:
            artist: Artist name
            title: Song title
            template: Template filename (without path)
            album: Optional album name
            output_path: Path where to save the overlay

        Raises:
            FileNotFoundError: If template doesn't exist
        """
        template_path = os.path.join(self.config.templates_path, template)
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Template not found: {template_path}")

        # Load template
        img = Image.open(template_path).convert("RGBA")
        draw = ImageDraw.Draw(img)

        # For now, use basic text overlay on template
        # In a real implementation, you'd have template metadata
        # specifying text positions, fonts, colors, etc.

        # This is a simplified version
        font: Union[FreeTypeFont, ImageFont.ImageFont]
        try:
            font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                self.config.overlay_font_size,
            )
        except OSError:
            font = ImageFont.load_default()

        text_color = self._hex_to_rgba(self.config.overlay_font_color, 255)
        text = f"{artist} - {title}"

        # Position text in lower third
        width, height = img.size
        padding = 20
        y_pos = int(height * 0.8)

        draw.text((padding, y_pos), text, fill=text_color, font=font)

        # Save
        img.save(output_path, "PNG")

    def cleanup_old_overlays(self, older_than_hours: Optional[int] = None) -> int:
        """
        Remove overlay files older than specified hours.

        Args:
            older_than_hours: Age threshold in hours. If None, uses config value.

        Returns:
            Number of files deleted
        """
        if older_than_hours is None:
            older_than_hours = self.config.overlay_ttl_hours

        cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
        overlays_dir = Path(self.config.overlays_path)

        if not overlays_dir.exists():
            return 0

        deleted_count = 0
        for overlay_file in overlays_dir.glob("*.png"):
            try:
                file_time = datetime.fromtimestamp(overlay_file.stat().st_mtime)
                if file_time < cutoff_time:
                    overlay_file.unlink()
                    deleted_count += 1
                    self.logger.debug(f"Deleted old overlay: {overlay_file}")
            except Exception as e:
                self.logger.warning(f"Failed to delete overlay {overlay_file}: {e}")

        if deleted_count > 0:
            self.logger.info(f"Cleaned up {deleted_count} old overlays")

        return deleted_count

    def _generate_cache_key(self, artist: str, title: str, album: str) -> str:
        """
        Generate a cache key for an overlay.

        Args:
            artist: Artist name
            title: Song title
            album: Album name

        Returns:
            MD5 hash of the combined text
        """
        combined = f"{artist}|{title}|{album}".lower().strip()
        return hashlib.md5(combined.encode()).hexdigest()

    def _is_overlay_fresh(self, overlay_path: str) -> bool:
        """
        Check if an overlay file exists and is still fresh.

        Args:
            overlay_path: Path to overlay file

        Returns:
            True if overlay exists and is within TTL
        """
        path = Path(overlay_path)
        if not path.exists():
            return False

        try:
            file_time = datetime.fromtimestamp(path.stat().st_mtime)
            cutoff_time = datetime.now() - timedelta(hours=self.config.overlay_ttl_hours)
            return file_time >= cutoff_time
        except Exception:
            return False

    def _hex_to_rgba(self, hex_color: str, alpha: int) -> Tuple[int, int, int, int]:
        """
        Convert hex color to RGBA tuple.

        Args:
            hex_color: Hex color string (e.g., "#FFFFFF")
            alpha: Alpha value (0-255)

        Returns:
            RGBA tuple
        """
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return (r, g, b, alpha)

    def _truncate_text(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: Union[FreeTypeFont, ImageFont.ImageFont],
        max_width: int,
    ) -> str:
        """
        Truncate text to fit within max width.

        Args:
            draw: ImageDraw object
            text: Text to truncate
            font: Font being used
            max_width: Maximum width in pixels

        Returns:
            Truncated text with "..." if needed
        """
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]

        if text_width <= max_width:
            return text

        # Binary search for the right length
        left, right = 0, len(text)
        while left < right:
            mid = (left + right + 1) // 2
            test_text = text[:mid] + "..."
            bbox = draw.textbbox((0, 0), test_text, font=font)
            test_width = bbox[2] - bbox[0]

            if test_width <= max_width:
                left = mid
            else:
                right = mid - 1

        return text[:left] + "..." if left > 0 else "..."
