# Overlay Templates

This directory contains PNG templates for video overlays.

## Template Format

Templates should be:
- PNG format with transparency (RGBA)
- Same resolution as target video (default: 1280x720)
- Designed for compositing with FFmpeg overlay filter

## Creating Templates

Templates can be created in any graphics editor that supports transparency:
- GIMP (free)
- Photoshop
- Affinity Designer
- Figma

### Basic Template Structure

1. Create a transparent canvas at target resolution
2. Add semi-transparent overlays (lower thirds, corner graphics, etc.)
3. Leave space for dynamic text elements
4. Export as PNG with transparency

## Example Templates

- `basic_lowerthird.png` - Simple lower third bar
- `corner_badge.png` - Corner branding element
- `fullscreen_overlay.png` - Full-screen overlay with text areas

## Using Templates

Templates are referenced by filename in the overlay generation API:

```python
from asset_manager import AssetManager

manager = AssetManager()
overlay_path = manager.generate_overlay(
    artist="Artist Name",
    title="Song Title",
    template="basic_lowerthird.png"  # Template filename
)
```

## Notes

- Template metadata (text positions, fonts, colors) can be defined in companion JSON files
- For now, text is overlaid at predefined positions
- Future enhancement: Template metadata system for precise text placement



