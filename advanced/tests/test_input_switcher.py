"""Tests for input switcher."""

import asyncio
import os
import tempfile
from pathlib import Path

import pytest

from advanced.input_switcher import InputSwitcher, SwitchStrategy, InputState


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def test_video_file(temp_dir):
    """Create a test video file."""
    video_path = os.path.join(temp_dir, "test_video.mp4")
    # Create empty file (we're not actually testing FFmpeg here)
    Path(video_path).touch()
    return video_path


@pytest.fixture
def switcher(temp_dir):
    """Create input switcher."""
    return InputSwitcher(
        strategy=SwitchStrategy.SYMLINK,
        temp_dir=temp_dir,
    )


class TestInputSwitcher:
    """Test suite for InputSwitcher."""
    
    def test_init(self, temp_dir):
        """Test initialization."""
        switcher = InputSwitcher(temp_dir=temp_dir)
        
        assert switcher.strategy == SwitchStrategy.SYMLINK
        assert switcher.temp_dir == Path(temp_dir)
        assert os.path.exists(temp_dir)
    
    @pytest.mark.asyncio
    async def test_prepare_input_symlink(self, switcher, test_video_file):
        """Test preparing input with symlink strategy."""
        prepared_path = await switcher.prepare_input(test_video_file, slot=0)
        
        assert os.path.exists(prepared_path)
        assert os.path.islink(prepared_path)
        assert os.path.realpath(prepared_path) == os.path.abspath(test_video_file)
    
    @pytest.mark.asyncio
    async def test_prepare_input_invalid_slot(self, switcher, test_video_file):
        """Test preparing input with invalid slot raises error."""
        with pytest.raises(ValueError, match="Invalid slot"):
            await switcher.prepare_input(test_video_file, slot=2)
    
    @pytest.mark.asyncio
    async def test_prepare_input_missing_file(self, switcher, temp_dir):
        """Test preparing input with missing file raises error."""
        missing_file = os.path.join(temp_dir, "missing.mp4")
        
        with pytest.raises(FileNotFoundError):
            await switcher.prepare_input(missing_file, slot=0)
    
    @pytest.mark.asyncio
    async def test_switch_input(self, switcher, temp_dir):
        """Test switching input."""
        # Create two test files
        video1 = os.path.join(temp_dir, "video1.mp4")
        video2 = os.path.join(temp_dir, "video2.mp4")
        Path(video1).touch()
        Path(video2).touch()
        
        # Prepare initial input
        await switcher.prepare_input(video1, slot=0)
        
        # Switch to second input
        success = await switcher.switch_input(video2)
        
        assert success is True
        assert switcher._switch_count == 1
        assert switcher._active_slot == 1
    
    @pytest.mark.asyncio
    async def test_update_symlink(self, switcher, temp_dir):
        """Test updating symlink."""
        video1 = os.path.join(temp_dir, "video1.mp4")
        video2 = os.path.join(temp_dir, "video2.mp4")
        Path(video1).touch()
        Path(video2).touch()
        
        # Prepare initial input
        await switcher.prepare_input(video1, slot=0)
        
        # Update symlink
        success = await switcher.update_symlink(slot=0, new_path=video2)
        
        assert success is True
        
        # Verify symlink points to new file
        symlink_path = switcher.temp_dir / "input_0.mp4"
        assert os.path.realpath(symlink_path) == os.path.abspath(video2)
    
    @pytest.mark.asyncio
    async def test_get_active_input(self, switcher, test_video_file):
        """Test getting active input."""
        await switcher.prepare_input(test_video_file, slot=0)
        
        active = switcher.get_active_input()
        
        assert active is not None
        assert active.slot == 0
        assert active.path == test_video_file
    
    @pytest.mark.asyncio
    async def test_get_inactive_input(self, switcher, temp_dir):
        """Test getting inactive input."""
        video1 = os.path.join(temp_dir, "video1.mp4")
        video2 = os.path.join(temp_dir, "video2.mp4")
        Path(video1).touch()
        Path(video2).touch()
        
        await switcher.prepare_input(video1, slot=0)
        await switcher.prepare_input(video2, slot=1)
        
        inactive = switcher.get_inactive_input()
        
        assert inactive is not None
        assert inactive.slot == 1
        assert inactive.path == video2
    
    @pytest.mark.asyncio
    async def test_get_input_paths(self, switcher, temp_dir):
        """Test getting both input paths."""
        video1 = os.path.join(temp_dir, "video1.mp4")
        video2 = os.path.join(temp_dir, "video2.mp4")
        Path(video1).touch()
        Path(video2).touch()
        
        path0 = await switcher.prepare_input(video1, slot=0)
        path1 = await switcher.prepare_input(video2, slot=1)
        
        paths = switcher.get_input_paths()
        
        assert paths == (path0, path1)
    
    @pytest.mark.asyncio
    async def test_register_callback(self, switcher, temp_dir):
        """Test registering callback."""
        callback_called = False
        callback_args = {}
        
        async def test_callback(video_path: str, slot: int):
            nonlocal callback_called, callback_args
            callback_called = True
            callback_args = {"video_path": video_path, "slot": slot}
        
        switcher.register_callback(test_callback)
        
        video1 = os.path.join(temp_dir, "video1.mp4")
        video2 = os.path.join(temp_dir, "video2.mp4")
        Path(video1).touch()
        Path(video2).touch()
        
        await switcher.prepare_input(video1, slot=0)
        await switcher.switch_input(video2)
        
        # Small delay for async callback
        await asyncio.sleep(0.1)
        
        assert callback_called is True
        assert callback_args["video_path"] == video2
        assert callback_args["slot"] == 1
    
    @pytest.mark.asyncio
    async def test_cleanup(self, switcher, temp_dir):
        """Test cleanup removes symlinks."""
        video = os.path.join(temp_dir, "video.mp4")
        Path(video).touch()
        
        await switcher.prepare_input(video, slot=0)
        
        symlink_path = switcher.temp_dir / "input_0.mp4"
        assert os.path.exists(symlink_path)
        
        await switcher.cleanup()
        
        assert not os.path.exists(symlink_path)
    
    def test_get_stats(self, switcher):
        """Test getting statistics."""
        stats = switcher.get_stats()
        
        assert isinstance(stats, dict)
        assert "strategy" in stats
        assert "switch_count" in stats
        assert "active_slot" in stats
        assert stats["strategy"] == "symlink"
        assert stats["switch_count"] == 0
        assert stats["active_slot"] == 0


class TestSwitchStrategy:
    """Test SwitchStrategy enum."""
    
    def test_strategies_exist(self):
        """Test that all expected strategies exist."""
        assert SwitchStrategy.SYMLINK == "symlink"
        assert SwitchStrategy.CONCAT == "concat"
        assert SwitchStrategy.HLS == "hls"
        assert SwitchStrategy.DUAL_PROCESS == "dual_process"



