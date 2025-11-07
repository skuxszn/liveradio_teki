"""Filter Graph Builder for FFmpeg.

Constructs complex filter graphs for dual-input crossfading, including
dynamic xfade transitions between video loops.
"""

import logging
from typing import List, Optional, Tuple

from advanced.config import AdvancedConfig

logger = logging.getLogger(__name__)


class FilterGraphBuilder:
    """Builds FFmpeg filter graphs for seamless video crossfading.

    The filter graph manages two video inputs and performs crossfade
    transitions between them. The audio is taken from a separate live stream.

    Example filter graph:
        [0:v]setpts=PTS-STARTPTS,scale=1280:720,format=yuv420p[v0];
        [1:v]setpts=PTS-STARTPTS,scale=1280:720,format=yuv420p[v1];
        [v0][v1]xfade=transition=fade:duration=2:offset=0[vout]
    """

    # Available xfade transitions
    TRANSITIONS = [
        "fade",
        "wipeleft",
        "wiperight",
        "wipeup",
        "wipedown",
        "slideleft",
        "slideright",
        "slideup",
        "slidedown",
        "smoothleft",
        "smoothright",
        "smoothup",
        "smoothdown",
        "circlecrop",
        "rectcrop",
        "distance",
        "fadeblack",
        "fadewhite",
        "radial",
        "smoothleft",
        "smoothright",
        "smoothup",
        "smoothdown",
        "circleopen",
        "circleclose",
        "vertopen",
        "vertclose",
        "horzopen",
        "horzclose",
        "dissolve",
        "pixelize",
    ]

    def __init__(self, config: AdvancedConfig):
        """Initialize filter graph builder.

        Args:
            config: Advanced configuration
        """
        self.config = config

        if config.crossfade_transition not in self.TRANSITIONS:
            logger.warning(f"Unknown transition '{config.crossfade_transition}', using 'fade'")
            self.config.crossfade_transition = "fade"

    def build_dual_input_filter(
        self,
        offset_seconds: float = 0.0,
        input0_name: str = "0:v",
        input1_name: str = "1:v",
    ) -> str:
        """Build filter graph for dual video inputs with crossfade.

        Args:
            offset_seconds: Time offset for xfade (when to start transition)
            input0_name: Name of first video input
            input1_name: Name of second video input

        Returns:
            Complete filter_complex string for FFmpeg
        """
        # Normalize and prepare video inputs
        v0_filters = self._build_video_normalization(input0_name, "v0")
        v1_filters = self._build_video_normalization(input1_name, "v1")

        # Build xfade transition
        xfade_filter = self._build_xfade("[v0]", "[v1]", offset_seconds, "[vout]")

        # Combine all filters
        filter_graph = f"{v0_filters};{v1_filters};{xfade_filter}"

        logger.debug(f"Built filter graph: {filter_graph}")
        return filter_graph

    def build_single_input_filter(
        self,
        input_name: str = "0:v",
        output_name: str = "[vout]",
    ) -> str:
        """Build filter graph for single video input (no crossfade).

        Used for the initial stream before any track changes.

        Args:
            input_name: Name of video input
            output_name: Name of output

        Returns:
            Filter string for single input
        """
        return self._build_video_normalization(input_name, output_name.strip("[]"))

    def _build_video_normalization(
        self,
        input_name: str,
        output_name: str,
    ) -> str:
        """Build filters to normalize video input.

        Args:
            input_name: Input stream name (e.g., "0:v")
            output_name: Output label (e.g., "v0")

        Returns:
            Filter string for normalization
        """
        filters = [
            f"[{input_name}]" if not input_name.startswith("[") else input_name,
            "setpts=PTS-STARTPTS",  # Reset timestamps
            f"scale={self.config.resolution}",  # Scale to target resolution
            f"format={self.config.pixel_format}",  # Convert pixel format
            f"fps={self.config.framerate}",  # Set framerate
        ]

        # Add fade-in to the first input only
        if input_name == "0:v":
            fade_frames = int(self.config.crossfade_duration * self.config.framerate)
            filters.insert(1, f"fade=t=in:st=0:d={self.config.crossfade_duration}")

        filter_str = ",".join(filters[1:])
        return f"[{input_name.strip('[]')}]{filter_str}[{output_name}]"

    def _build_xfade(
        self,
        input0: str,
        input1: str,
        offset: float,
        output: str,
    ) -> str:
        """Build xfade filter.

        Args:
            input0: First input label (e.g., "[v0]")
            input1: Second input label (e.g., "[v1]")
            offset: Time offset for transition
            output: Output label (e.g., "[vout]")

        Returns:
            xfade filter string
        """
        return (
            f"{input0}{input1}xfade="
            f"transition={self.config.crossfade_transition}:"
            f"duration={self.config.crossfade_duration}:"
            f"offset={offset}"
            f"{output}"
        )

    def build_audio_fade_filter(
        self,
        fade_in: bool = True,
        duration: Optional[float] = None,
    ) -> str:
        """Build audio fade filter.

        Args:
            fade_in: If True, fade in; if False, fade out
            duration: Fade duration (uses config default if None)

        Returns:
            Audio fade filter string
        """
        duration = duration or self.config.crossfade_duration
        fade_type = "in" if fade_in else "out"

        return f"afade=t={fade_type}:ss=0:d={duration}"

    def estimate_transition_offset(
        self,
        track_duration: float,
        overlap_before_end: float = 2.0,
    ) -> float:
        """Calculate when to start the crossfade transition.

        Args:
            track_duration: Duration of current track in seconds
            overlap_before_end: How many seconds before end to start transition

        Returns:
            Offset time in seconds
        """
        # Start crossfade before track ends
        offset = max(0, track_duration - overlap_before_end)
        logger.debug(
            f"Calculated transition offset: {offset}s "
            f"(track_duration={track_duration}s, overlap={overlap_before_end}s)"
        )
        return offset

    def validate_transition(self) -> Tuple[bool, str]:
        """Validate that the configured transition is supported.

        Returns:
            Tuple of (is_valid, message)
        """
        if self.config.crossfade_transition in self.TRANSITIONS:
            return True, f"Transition '{self.config.crossfade_transition}' is valid"
        else:
            return False, (
                f"Transition '{self.config.crossfade_transition}' is not supported. "
                f"Available transitions: {', '.join(self.TRANSITIONS[:5])}..."
            )

    def get_available_transitions(self) -> List[str]:
        """Get list of available xfade transitions.

        Returns:
            List of transition names
        """
        return self.TRANSITIONS.copy()
