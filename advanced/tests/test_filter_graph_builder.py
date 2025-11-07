"""Tests for filter graph builder."""

import pytest

from advanced.config import AdvancedConfig
from advanced.filter_graph_builder import FilterGraphBuilder


class TestFilterGraphBuilder:
    """Test suite for FilterGraphBuilder."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return AdvancedConfig(
            resolution="1280:720",
            framerate=30,
            pixel_format="yuv420p",
            crossfade_duration=2.0,
            crossfade_transition="fade",
        )
    
    @pytest.fixture
    def builder(self, config):
        """Create filter graph builder."""
        return FilterGraphBuilder(config)
    
    def test_init(self, config):
        """Test initialization."""
        builder = FilterGraphBuilder(config)
        assert builder.config == config
    
    def test_init_invalid_transition(self, config):
        """Test initialization with invalid transition falls back to fade."""
        config.crossfade_transition = "invalid_transition"
        builder = FilterGraphBuilder(config)
        
        assert builder.config.crossfade_transition == "fade"
    
    def test_build_dual_input_filter(self, builder):
        """Test building dual input filter graph."""
        filter_graph = builder.build_dual_input_filter()
        
        assert "[0:v]" in filter_graph or "0:v" in filter_graph
        assert "[1:v]" in filter_graph or "1:v" in filter_graph
        assert "xfade" in filter_graph
        assert "scale=1280:720" in filter_graph
        assert "format=yuv420p" in filter_graph
        assert "fps=30" in filter_graph
        assert "transition=fade" in filter_graph
        assert "duration=2.0" in filter_graph
    
    def test_build_dual_input_filter_custom_offset(self, builder):
        """Test building filter with custom offset."""
        filter_graph = builder.build_dual_input_filter(offset_seconds=5.0)
        
        assert "offset=5.0" in filter_graph
    
    def test_build_dual_input_filter_custom_inputs(self, builder):
        """Test building filter with custom input names."""
        filter_graph = builder.build_dual_input_filter(
            input0_name="2:v",
            input1_name="3:v",
        )
        
        assert "2:v" in filter_graph
        assert "3:v" in filter_graph
    
    def test_build_single_input_filter(self, builder):
        """Test building single input filter."""
        filter_str = builder.build_single_input_filter()
        
        assert "0:v" in filter_str
        assert "scale=1280:720" in filter_str
        assert "format=yuv420p" in filter_str
        assert "fps=30" in filter_str
        assert "fade=t=in" in filter_str  # Should have fade-in
    
    def test_build_audio_fade_filter_in(self, builder):
        """Test building audio fade-in filter."""
        filter_str = builder.build_audio_fade_filter(fade_in=True)
        
        assert "afade=t=in" in filter_str
        assert "d=2.0" in filter_str
    
    def test_build_audio_fade_filter_out(self, builder):
        """Test building audio fade-out filter."""
        filter_str = builder.build_audio_fade_filter(fade_in=False)
        
        assert "afade=t=out" in filter_str
    
    def test_build_audio_fade_filter_custom_duration(self, builder):
        """Test building audio fade filter with custom duration."""
        filter_str = builder.build_audio_fade_filter(duration=3.5)
        
        assert "d=3.5" in filter_str
    
    def test_estimate_transition_offset(self, builder):
        """Test estimating transition offset."""
        offset = builder.estimate_transition_offset(track_duration=180.0)
        
        assert offset == 178.0  # 180 - 2 (default overlap)
    
    def test_estimate_transition_offset_custom_overlap(self, builder):
        """Test estimating transition offset with custom overlap."""
        offset = builder.estimate_transition_offset(
            track_duration=180.0,
            overlap_before_end=5.0,
        )
        
        assert offset == 175.0  # 180 - 5
    
    def test_estimate_transition_offset_short_track(self, builder):
        """Test estimating transition offset for very short track."""
        offset = builder.estimate_transition_offset(track_duration=1.0)
        
        assert offset == 0.0  # Should not be negative
    
    def test_validate_transition_valid(self, builder):
        """Test validating valid transition."""
        is_valid, message = builder.validate_transition()
        
        assert is_valid is True
        assert "valid" in message.lower()
    
    def test_validate_transition_invalid(self, config):
        """Test validating invalid transition."""
        config.crossfade_transition = "invalid_transition"
        # Note: __init__ will reset it to "fade"
        builder = FilterGraphBuilder.__new__(FilterGraphBuilder)
        builder.config = config
        
        is_valid, message = builder.validate_transition()
        
        assert is_valid is False
        assert "not supported" in message.lower()
    
    def test_get_available_transitions(self, builder):
        """Test getting list of available transitions."""
        transitions = builder.get_available_transitions()
        
        assert isinstance(transitions, list)
        assert len(transitions) > 0
        assert "fade" in transitions
        assert "wipeleft" in transitions
        assert "dissolve" in transitions
    
    def test_transitions_constant(self):
        """Test that TRANSITIONS constant has expected values."""
        assert "fade" in FilterGraphBuilder.TRANSITIONS
        assert "wipeleft" in FilterGraphBuilder.TRANSITIONS
        assert "wiperight" in FilterGraphBuilder.TRANSITIONS
        assert len(FilterGraphBuilder.TRANSITIONS) > 20



