"""
Tests for the overlay_generator module.
"""

import os
import time
from pathlib import Path

import pytest
from PIL import Image

from asset_manager.config import AssetConfig
from asset_manager.overlay_generator import OverlayGenerator


def test_overlay_generator_initialization(test_config: AssetConfig):
    """Test OverlayGenerator initialization."""
    generator = OverlayGenerator(test_config)
    assert generator.config == test_config


def test_overlay_generator_ensures_directories(test_config: AssetConfig):
    """Test that generator creates required directories."""
    # Remove directories
    import shutil

    if os.path.exists(test_config.overlays_path):
        shutil.rmtree(test_config.overlays_path)
    if os.path.exists(test_config.templates_path):
        shutil.rmtree(test_config.templates_path)

    # Create generator (which should create directories)
    OverlayGenerator(test_config)

    # Check directories exist
    assert os.path.exists(test_config.overlays_path)
    assert os.path.exists(test_config.templates_path)


def test_generate_basic_overlay(test_config: AssetConfig):
    """Test generating a basic overlay."""
    generator = OverlayGenerator(test_config)

    overlay_path = generator.generate_overlay(
        artist="Test Artist",
        title="Test Title",
    )

    # Check file was created
    assert os.path.exists(overlay_path)

    # Check it's a valid PNG
    img = Image.open(overlay_path)
    assert img.format == "PNG"
    assert img.size == (1280, 720)


def test_generate_overlay_with_album(test_config: AssetConfig):
    """Test generating overlay with album information."""
    generator = OverlayGenerator(test_config)

    overlay_path = generator.generate_overlay(
        artist="Test Artist",
        title="Test Title",
        album="Test Album",
    )

    assert os.path.exists(overlay_path)


def test_generate_overlay_caching(test_config: AssetConfig):
    """Test that overlays are cached."""
    generator = OverlayGenerator(test_config)

    # Generate overlay
    overlay_path1 = generator.generate_overlay(
        artist="Test Artist",
        title="Test Title",
    )

    # Get modification time
    mtime1 = os.path.getmtime(overlay_path1)

    # Wait a bit
    time.sleep(0.1)

    # Generate same overlay again
    overlay_path2 = generator.generate_overlay(
        artist="Test Artist",
        title="Test Title",
    )

    # Should be same file
    assert overlay_path1 == overlay_path2

    # Modification time should be same (cached)
    mtime2 = os.path.getmtime(overlay_path2)
    assert mtime1 == mtime2


def test_generate_cache_key(test_config: AssetConfig):
    """Test cache key generation."""
    generator = OverlayGenerator(test_config)

    key1 = generator._generate_cache_key("Artist", "Title", "Album")
    key2 = generator._generate_cache_key("Artist", "Title", "Album")
    key3 = generator._generate_cache_key("Different", "Title", "Album")

    # Same input should produce same key
    assert key1 == key2

    # Different input should produce different key
    assert key1 != key3


def test_is_overlay_fresh(test_config: AssetConfig):
    """Test overlay freshness check."""
    generator = OverlayGenerator(test_config)

    # Create a file
    test_file = os.path.join(test_config.overlays_path, "test.png")
    Path(test_file).touch()

    # Should be fresh
    assert generator._is_overlay_fresh(test_file) is True

    # Non-existent file should not be fresh
    assert generator._is_overlay_fresh("/nonexistent/file.png") is False


def test_cleanup_old_overlays(test_config: AssetConfig):
    """Test cleaning up old overlays."""
    generator = OverlayGenerator(test_config)

    # Create some test overlays
    old_file = os.path.join(test_config.overlays_path, "old.png")
    new_file = os.path.join(test_config.overlays_path, "new.png")

    Path(old_file).touch()
    Path(new_file).touch()

    # Make old file old (modify access/modification times)
    old_time = time.time() - (2 * 60 * 60)  # 2 hours ago
    os.utime(old_file, (old_time, old_time))

    # Clean up files older than 1 hour
    deleted_count = generator.cleanup_old_overlays(older_than_hours=1)

    # Old file should be deleted
    assert not os.path.exists(old_file)
    assert os.path.exists(new_file)
    assert deleted_count == 1


def test_hex_to_rgba(test_config: AssetConfig):
    """Test hex to RGBA conversion."""
    generator = OverlayGenerator(test_config)

    # Test white
    rgba = generator._hex_to_rgba("#FFFFFF", 255)
    assert rgba == (255, 255, 255, 255)

    # Test black with transparency
    rgba = generator._hex_to_rgba("#000000", 128)
    assert rgba == (0, 0, 0, 128)

    # Test color
    rgba = generator._hex_to_rgba("#FF0000", 200)
    assert rgba == (255, 0, 0, 200)


def test_truncate_text(test_config: AssetConfig):
    """Test text truncation."""
    from PIL import ImageDraw, ImageFont

    generator = OverlayGenerator(test_config)
    img = Image.new("RGB", (100, 100))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    # Short text should not be truncated
    short_text = "Short"
    result = generator._truncate_text(draw, short_text, font, 1000)
    assert result == short_text

    # Long text should be truncated
    long_text = "This is a very long text that should be truncated"
    result = generator._truncate_text(draw, long_text, font, 50)
    assert "..." in result
    assert len(result) < len(long_text)


def test_generate_from_template(test_config: AssetConfig, test_image_path: str):
    """Test generating overlay from template."""
    generator = OverlayGenerator(test_config)

    # Copy test image to templates directory as a template
    template_name = "test_template.png"
    template_path = os.path.join(test_config.templates_path, template_name)

    import shutil

    shutil.copy(test_image_path, template_path)

    # Generate overlay from template
    overlay_path = generator.generate_overlay(
        artist="Test Artist",
        title="Test Title",
        template=template_name,
    )

    assert os.path.exists(overlay_path)


def test_generate_from_nonexistent_template(test_config: AssetConfig):
    """Test generating overlay from non-existent template."""
    generator = OverlayGenerator(test_config)

    with pytest.raises(RuntimeError):
        generator.generate_overlay(
            artist="Test Artist",
            title="Test Title",
            template="nonexistent.png",
        )
