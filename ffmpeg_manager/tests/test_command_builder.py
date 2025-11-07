"""
Tests for FFmpeg command builder.
"""

import pytest

from ffmpeg_manager.command_builder import FFmpegCommandBuilder, create_command_builder
from ffmpeg_manager.config import EncodingPreset, FFmpegConfig


class TestFFmpegCommandBuilder:
    """Test FFmpeg command builder."""

    def test_initialization(self, test_config: FFmpegConfig):
        """Test command builder initialization."""
        builder = FFmpegCommandBuilder(test_config)

        assert builder.config == test_config
        assert builder.encoding_config is not None

    def test_build_basic_command(self, command_builder: FFmpegCommandBuilder, test_loop_file):
        """Test building a basic FFmpeg command."""
        cmd = command_builder.build_command(str(test_loop_file))

        # Check basic structure
        assert cmd[0] == "ffmpeg"
        assert "-re" in cmd  # Real-time flag
        assert "-i" in cmd  # Input flag
        assert str(test_loop_file) in cmd
        assert "-f" in cmd  # Format flag
        assert "flv" in cmd  # FLV format

    def test_build_command_with_custom_urls(
        self, command_builder: FFmpegCommandBuilder, test_loop_file
    ):
        """Test building command with custom audio URL and RTMP endpoint."""
        custom_audio = "http://custom:8000/audio"
        custom_rtmp = "rtmp://custom:1935/live/custom"

        cmd = command_builder.build_command(
            str(test_loop_file),
            audio_url=custom_audio,
            rtmp_endpoint=custom_rtmp,
        )

        assert custom_audio in cmd
        assert custom_rtmp in cmd

    def test_build_command_with_fade_in(
        self, command_builder: FFmpegCommandBuilder, test_loop_file
    ):
        """Test building command with fade-in transition."""
        cmd = command_builder.build_command(str(test_loop_file), fade_in=True)

        # Check for fade filters
        cmd_str = " ".join(cmd)
        assert "fade=t=in" in cmd_str
        assert "afade=t=in" in cmd_str

    def test_build_command_without_fade(
        self, command_builder: FFmpegCommandBuilder, test_loop_file
    ):
        """Test building command without fade-in."""
        cmd = command_builder.build_command(str(test_loop_file), fade_in=False)

        # Fade filters should not be present
        cmd_str = " ".join(cmd)
        assert "fade=t=in" not in cmd_str
        assert "afade=t=in" not in cmd_str

    def test_build_command_empty_loop_path(self, command_builder: FFmpegCommandBuilder):
        """Test building command with empty loop path."""
        with pytest.raises(ValueError, match="loop_path cannot be empty"):
            command_builder.build_command("")

    def test_video_encoding_options(
        self, command_builder: FFmpegCommandBuilder, test_loop_file
    ):
        """Test video encoding options in command."""
        cmd = command_builder.build_command(str(test_loop_file))

        # Check for essential video options
        assert "-c:v" in cmd  # Video codec
        assert "-b:v" in cmd  # Video bitrate
        assert "-g" in cmd  # Keyframe interval
        assert "-pix_fmt" in cmd  # Pixel format

    def test_audio_encoding_options(
        self, command_builder: FFmpegCommandBuilder, test_loop_file
    ):
        """Test audio encoding options in command."""
        cmd = command_builder.build_command(str(test_loop_file))

        # Check for essential audio options
        assert "-c:a" in cmd  # Audio codec
        assert "-b:a" in cmd  # Audio bitrate
        assert "-ar" in cmd  # Audio sample rate
        assert "-ac" in cmd  # Audio channels

    def test_stream_looping(self, command_builder: FFmpegCommandBuilder, test_loop_file):
        """Test that video stream looping is configured."""
        cmd = command_builder.build_command(str(test_loop_file))

        assert "-stream_loop" in cmd
        assert "-1" in cmd  # Loop indefinitely

    def test_get_command_string(
        self, command_builder: FFmpegCommandBuilder, test_loop_file
    ):
        """Test getting command as string."""
        cmd_str = command_builder.get_command_string(str(test_loop_file))

        assert isinstance(cmd_str, str)
        assert "ffmpeg" in cmd_str
        assert str(test_loop_file) in cmd_str

    def test_validate_encoding_compatibility(
        self, command_builder: FFmpegCommandBuilder
    ):
        """Test encoding compatibility validation."""
        # Currently always returns True, but should not raise errors
        result = command_builder.validate_encoding_compatibility()
        assert isinstance(result, bool)


class TestCommandBuilderWithDifferentPresets:
    """Test command builder with different encoding presets."""

    def test_720p_fast_preset(self, test_loop_file):
        """Test command with 720p fast preset."""
        config = FFmpegConfig(encoding_preset=EncodingPreset.PRESET_720P_FAST)
        builder = FFmpegCommandBuilder(config)
        cmd = builder.build_command(str(test_loop_file))

        cmd_str = " ".join(cmd)
        assert "scale=1280:720" in cmd_str
        assert "libx264" in cmd

    def test_1080p_nvenc_preset(self, test_loop_file):
        """Test command with 1080p NVENC preset."""
        config = FFmpegConfig(encoding_preset=EncodingPreset.PRESET_1080P_NVENC)
        builder = FFmpegCommandBuilder(config)
        cmd = builder.build_command(str(test_loop_file))

        cmd_str = " ".join(cmd)
        assert "scale=1920:1080" in cmd_str
        assert "h264_nvenc" in cmd

    def test_480p_test_preset(self, test_loop_file):
        """Test command with 480p test preset."""
        config = FFmpegConfig(encoding_preset=EncodingPreset.PRESET_480P_TEST)
        builder = FFmpegCommandBuilder(config)
        cmd = builder.build_command(str(test_loop_file))

        cmd_str = " ".join(cmd)
        assert "scale=854:480" in cmd_str
        assert "ultrafast" in cmd


class TestCreateCommandBuilder:
    """Test command builder factory function."""

    def test_create_with_config(self, test_config: FFmpegConfig):
        """Test creating command builder with config."""
        builder = create_command_builder(test_config)

        assert isinstance(builder, FFmpegCommandBuilder)
        assert builder.config == test_config

    def test_create_without_config(self):
        """Test creating command builder without config (uses default)."""
        builder = create_command_builder()

        assert isinstance(builder, FFmpegCommandBuilder)
        assert builder.config is not None


class TestCommandBuilderPrivateMethods:
    """Test private methods of command builder."""

    def test_build_global_options(self, command_builder: FFmpegCommandBuilder):
        """Test building global FFmpeg options."""
        options = command_builder._build_global_options()

        assert "-re" in options
        assert "-loglevel" in options
        assert "-hide_banner" in options

    def test_build_video_input(self, command_builder: FFmpegCommandBuilder):
        """Test building video input options."""
        options = command_builder._build_video_input("/path/to/loop.mp4")

        assert "-stream_loop" in options
        assert "-i" in options
        assert "/path/to/loop.mp4" in options

    def test_build_audio_input(self, command_builder: FFmpegCommandBuilder):
        """Test building audio input options."""
        options = command_builder._build_audio_input("http://test:8000/stream")

        assert "-i" in options
        assert "http://test:8000/stream" in options

    def test_build_output_options(self, command_builder: FFmpegCommandBuilder):
        """Test building output options."""
        options = command_builder._build_output_options("rtmp://test/live")

        assert "-f" in options
        assert "flv" in options
        assert "rtmp://test/live" in options



