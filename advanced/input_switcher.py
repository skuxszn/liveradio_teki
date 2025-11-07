"""Input Switcher for Dynamic Video Input Management.

Manages dynamic switching of video inputs for the persistent FFmpeg process.
Since FFmpeg doesn't natively support dynamic input reloading, this module
provides strategies for achieving seamless transitions.
"""

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class SwitchStrategy(str, Enum):
    """Strategy for switching video inputs."""
    
    SYMLINK = "symlink"  # Use symlinks and force FFmpeg to reload
    CONCAT = "concat"  # Use concat protocol
    HLS = "hls"  # Use HLS intermediate format
    DUAL_PROCESS = "dual_process"  # Maintain two FFmpeg processes


@dataclass
class InputState:
    """State of a video input."""
    
    slot: int  # 0 or 1 (dual input slots)
    path: str
    is_active: bool
    loaded_at: datetime
    symlink_path: Optional[str] = None


class InputSwitcher:
    """Manages dynamic switching of video inputs.
    
    This class provides mechanisms to switch video inputs in a running
    FFmpeg process. Since FFmpeg doesn't support hot-swapping inputs,
    we use various strategies:
    
    1. Symlink Strategy: Create symlinks and signal FFmpeg to reload
    2. Concat Strategy: Use concat demuxer with file updates
    3. HLS Strategy: Use HLS as intermediate format
    4. Dual Process Strategy: Maintain two processes and switch outputs
    
    For most use cases, the symlink strategy provides the best balance
    of performance and reliability.
    """
    
    def __init__(
        self,
        strategy: SwitchStrategy = SwitchStrategy.SYMLINK,
        temp_dir: str = "/tmp/radio_inputs",
    ):
        """Initialize input switcher.
        
        Args:
            strategy: Strategy to use for switching
            temp_dir: Directory for temporary files (symlinks, concat files)
        """
        self.strategy = strategy
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Track current state
        self._slots = {
            0: None,  # First input slot
            1: None,  # Second input slot
        }
        self._active_slot = 0
        self._switch_count = 0
        
        # Callbacks
        self._on_switch_callbacks: list[Callable] = []
        
        logger.info(f"InputSwitcher initialized with strategy: {strategy}")
    
    async def prepare_input(
        self,
        video_path: str,
        slot: int = 0,
    ) -> str:
        """Prepare a video input for use.
        
        Depending on the strategy, this may create symlinks or other
        intermediate files.
        
        Args:
            video_path: Path to the video file
            slot: Input slot (0 or 1 for dual inputs)
        
        Returns:
            Path to use in FFmpeg command (may be symlink or original)
        
        Raises:
            ValueError: If slot is invalid
            FileNotFoundError: If video file doesn't exist
        """
        if slot not in [0, 1]:
            raise ValueError(f"Invalid slot: {slot}. Must be 0 or 1")
        
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        logger.info(f"Preparing input for slot {slot}: {video_path}")
        
        if self.strategy == SwitchStrategy.SYMLINK:
            return await self._prepare_symlink(video_path, slot)
        elif self.strategy == SwitchStrategy.CONCAT:
            return await self._prepare_concat(video_path, slot)
        elif self.strategy == SwitchStrategy.HLS:
            # For HLS, we use the original path
            return video_path
        else:
            # For dual process, use original path
            return video_path
    
    async def _prepare_symlink(self, video_path: str, slot: int) -> str:
        """Prepare input using symlink strategy.
        
        Args:
            video_path: Path to video file
            slot: Input slot
        
        Returns:
            Path to symlink
        """
        symlink_path = self.temp_dir / f"input_{slot}.mp4"
        
        # Remove existing symlink if present
        if symlink_path.exists():
            symlink_path.unlink()
        
        # Create new symlink
        symlink_path.symlink_to(os.path.abspath(video_path))
        
        logger.debug(f"Created symlink: {symlink_path} -> {video_path}")
        
        # Update state
        self._slots[slot] = InputState(
            slot=slot,
            path=video_path,
            is_active=False,
            loaded_at=datetime.now(),
            symlink_path=str(symlink_path),
        )
        
        return str(symlink_path)
    
    async def _prepare_concat(self, video_path: str, slot: int) -> str:
        """Prepare input using concat demuxer.
        
        Args:
            video_path: Path to video file
            slot: Input slot
        
        Returns:
            Path to concat file
        """
        concat_file = self.temp_dir / f"concat_{slot}.txt"
        
        # Write concat file
        with open(concat_file, "w") as f:
            f.write(f"file '{os.path.abspath(video_path)}'\n")
        
        logger.debug(f"Created concat file: {concat_file}")
        
        # Update state
        self._slots[slot] = InputState(
            slot=slot,
            path=video_path,
            is_active=False,
            loaded_at=datetime.now(),
        )
        
        return f"concat:{concat_file}"
    
    async def switch_input(
        self,
        new_video_path: str,
        crossfade_duration: float = 2.0,
    ) -> bool:
        """Switch to a new video input.
        
        Args:
            new_video_path: Path to new video file
            crossfade_duration: Duration of crossfade transition
        
        Returns:
            True if switch was successful
        """
        try:
            # Determine which slot to use for the new input
            next_slot = 1 - self._active_slot
            
            logger.info(
                f"Switching from slot {self._active_slot} to slot {next_slot}: "
                f"{new_video_path}"
            )
            
            # Prepare the new input
            prepared_path = await self.prepare_input(new_video_path, next_slot)
            
            # Update active slot
            if self._slots[self._active_slot]:
                self._slots[self._active_slot].is_active = False
            
            if self._slots[next_slot]:
                self._slots[next_slot].is_active = True
            
            self._active_slot = next_slot
            self._switch_count += 1
            
            # Trigger callbacks
            await self._trigger_callbacks(new_video_path, next_slot)
            
            logger.info(
                f"Input switched successfully (switch #{self._switch_count})"
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to switch input: {e}", exc_info=True)
            return False
    
    async def update_symlink(self, slot: int, new_path: str) -> bool:
        """Update a symlink to point to a new video file.
        
        This is used for hot-reloading during a running stream.
        
        Args:
            slot: Slot to update
            new_path: New video file path
        
        Returns:
            True if update was successful
        """
        if self.strategy != SwitchStrategy.SYMLINK:
            logger.warning("update_symlink only works with SYMLINK strategy")
            return False
        
        try:
            symlink_path = self.temp_dir / f"input_{slot}.mp4"
            
            # Remove old symlink
            if symlink_path.exists():
                symlink_path.unlink()
            
            # Create new symlink
            symlink_path.symlink_to(os.path.abspath(new_path))
            
            logger.info(f"Updated symlink for slot {slot}: {symlink_path} -> {new_path}")
            
            # Update state
            if self._slots[slot]:
                self._slots[slot].path = new_path
                self._slots[slot].loaded_at = datetime.now()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update symlink: {e}", exc_info=True)
            return False
    
    def get_active_input(self) -> Optional[InputState]:
        """Get currently active input state.
        
        Returns:
            InputState for active slot, or None if no active input
        """
        return self._slots[self._active_slot]
    
    def get_inactive_input(self) -> Optional[InputState]:
        """Get currently inactive input state.
        
        Returns:
            InputState for inactive slot, or None if no inactive input
        """
        inactive_slot = 1 - self._active_slot
        return self._slots[inactive_slot]
    
    def get_input_paths(self) -> tuple[Optional[str], Optional[str]]:
        """Get paths for both input slots.
        
        Returns:
            Tuple of (slot0_path, slot1_path)
        """
        return (
            self._slots[0].symlink_path if self._slots[0] else None,
            self._slots[1].symlink_path if self._slots[1] else None,
        )
    
    def register_callback(self, callback: Callable) -> None:
        """Register a callback to be called on input switch.
        
        Callback signature: async def callback(video_path: str, slot: int) -> None
        
        Args:
            callback: Async callback function
        """
        self._on_switch_callbacks.append(callback)
        logger.debug(f"Registered switch callback: {callback.__name__}")
    
    async def _trigger_callbacks(self, video_path: str, slot: int) -> None:
        """Trigger all registered callbacks.
        
        Args:
            video_path: Path to new video
            slot: Slot that was switched to
        """
        for callback in self._on_switch_callbacks:
            try:
                await callback(video_path, slot)
            except Exception as e:
                logger.error(f"Callback {callback.__name__} failed: {e}")
    
    async def cleanup(self) -> None:
        """Clean up temporary files."""
        logger.info("Cleaning up InputSwitcher resources")
        
        try:
            # Remove symlinks
            for slot in [0, 1]:
                symlink_path = self.temp_dir / f"input_{slot}.mp4"
                if symlink_path.exists():
                    symlink_path.unlink()
                
                concat_file = self.temp_dir / f"concat_{slot}.txt"
                if concat_file.exists():
                    concat_file.unlink()
            
            logger.info("Cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def get_stats(self) -> dict:
        """Get statistics about input switching.
        
        Returns:
            Dictionary with switch statistics
        """
        return {
            "strategy": self.strategy.value,
            "switch_count": self._switch_count,
            "active_slot": self._active_slot,
            "slot_0": self._slots[0].path if self._slots[0] else None,
            "slot_1": self._slots[1].path if self._slots[1] else None,
            "active_path": (
                self._slots[self._active_slot].path
                if self._slots[self._active_slot]
                else None
            ),
        }



