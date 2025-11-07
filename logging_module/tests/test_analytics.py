"""Unit tests for logging_module.analytics."""

import pytest
from datetime import datetime, timedelta

from logging_module.analytics import Analytics


class TestAnalytics:
    """Tests for Analytics class."""

    def test_initialization(self, test_analytics):
        """Test analytics initialization."""
        assert test_analytics is not None
        assert test_analytics.engine is not None

    def test_get_play_stats_empty_database(self, test_analytics):
        """Test getting play stats from empty database."""
        stats = test_analytics.get_play_stats(days=7)

        assert stats["total_plays"] == 0
        assert stats["unique_tracks"] == 0
        assert stats["total_duration_hours"] == 0.0
        assert stats["uptime_percent"] == 0.0

    def test_get_play_stats_with_data(self, test_analytics, populated_database):
        """Test getting play stats with populated database."""
        stats = test_analytics.get_play_stats(days=30)

        assert stats["total_plays"] > 0
        assert stats["unique_tracks"] > 0
        assert "start_date" in stats
        assert "end_date" in stats

    def test_get_play_stats_date_range(self, test_analytics):
        """Test getting play stats with custom date range."""
        start_date = datetime.now() - timedelta(days=14)
        end_date = datetime.now()

        stats = test_analytics.get_play_stats(start_date=start_date, end_date=end_date)

        assert stats is not None
        assert isinstance(stats, dict)

    def test_get_most_played_tracks_empty(self, test_analytics):
        """Test getting most played tracks from empty database."""
        tracks = test_analytics.get_most_played_tracks(days=7)

        assert tracks == []

    def test_get_most_played_tracks_with_data(self, test_analytics, populated_database):
        """Test getting most played tracks with populated database."""
        tracks = test_analytics.get_most_played_tracks(days=30, limit=5)

        assert isinstance(tracks, list)
        # Check structure of first track if any exist
        if tracks:
            track = tracks[0]
            assert "track_key" in track
            assert "artist" in track
            assert "title" in track
            assert "play_count" in track
            assert "total_duration_hours" in track

    def test_get_most_played_tracks_limit(self, test_analytics, populated_database):
        """Test limit parameter for most played tracks."""
        tracks = test_analytics.get_most_played_tracks(days=30, limit=3)

        assert len(tracks) <= 3

    def test_get_error_summary_empty(self, test_analytics):
        """Test getting error summary from empty database."""
        errors = test_analytics.get_error_summary(days=7)

        assert errors == []

    def test_get_error_summary_with_data(self, test_analytics, populated_database):
        """Test getting error summary with populated database."""
        errors = test_analytics.get_error_summary(days=30)

        assert isinstance(errors, list)
        # Check structure if any errors exist
        if errors:
            error = errors[0]
            assert "service" in error
            assert "severity" in error
            assert "error_count" in error
            assert "resolved_count" in error
            assert "unresolved_count" in error

    def test_get_hourly_play_distribution_empty(self, test_analytics):
        """Test getting hourly distribution from empty database."""
        distribution = test_analytics.get_hourly_play_distribution(days=7)

        assert isinstance(distribution, list)

    def test_get_hourly_play_distribution_with_data(self, test_analytics, populated_database):
        """Test getting hourly distribution with populated database."""
        distribution = test_analytics.get_hourly_play_distribution(days=30)

        assert isinstance(distribution, list)
        # Check structure if any data exists
        if distribution:
            hour_data = distribution[0]
            assert "hour_of_day" in hour_data
            assert "play_count" in hour_data
            assert "avg_duration_seconds" in hour_data
            assert 0 <= hour_data["hour_of_day"] <= 23

    def test_get_daily_summary(self, test_analytics, populated_database):
        """Test getting daily summary."""
        summary = test_analytics.get_daily_summary()

        assert isinstance(summary, dict)
        assert "date" in summary
        assert "total_plays" in summary
        assert "unique_tracks" in summary
        assert "uptime_percent" in summary
        assert "most_played_tracks" in summary
        assert "error_summary" in summary

    def test_get_daily_summary_specific_date(self, test_analytics):
        """Test getting daily summary for specific date."""
        specific_date = datetime.now() - timedelta(days=3)
        summary = test_analytics.get_daily_summary(date=specific_date)

        assert isinstance(summary, dict)
        assert "date" in summary

    def test_get_weekly_summary(self, test_analytics, populated_database):
        """Test getting weekly summary."""
        summary = test_analytics.get_weekly_summary()

        assert isinstance(summary, dict)
        assert "week_start" in summary
        assert "week_end" in summary
        assert "total_plays" in summary
        assert "unique_tracks" in summary
        assert "uptime_percent" in summary
        assert "most_played_tracks" in summary
        assert "error_summary" in summary
        assert "hourly_distribution" in summary

    def test_get_weekly_summary_specific_week(self, test_analytics):
        """Test getting weekly summary for specific week."""
        week_start = datetime.now() - timedelta(days=14)
        summary = test_analytics.get_weekly_summary(week_start=week_start)

        assert isinstance(summary, dict)

    def test_get_track_history_empty(self, test_analytics):
        """Test getting track history for non-existent track."""
        history = test_analytics.get_track_history("Unknown", "Track")

        assert history == []

    def test_get_track_history_with_data(self, test_analytics, populated_database):
        """Test getting track history with populated database."""
        # Use track that exists in populated_database
        history = test_analytics.get_track_history("Artist 0", "Song 0")

        assert isinstance(history, list)
        # Check structure if any history exists
        if history:
            play = history[0]
            assert "id" in play
            assert "started_at" in play
            assert "duration_seconds" in play

    def test_get_track_history_limit(self, test_analytics, populated_database):
        """Test limit parameter for track history."""
        history = test_analytics.get_track_history("Artist 0", "Song 0", limit=2)

        assert len(history) <= 2

    def test_get_uptime_by_day_empty(self, test_analytics):
        """Test getting uptime by day from empty database."""
        uptime = test_analytics.get_uptime_by_day(days=7)

        assert isinstance(uptime, list)

    def test_get_uptime_by_day_with_data(self, test_analytics, populated_database):
        """Test getting uptime by day with populated database."""
        uptime = test_analytics.get_uptime_by_day(days=30)

        assert isinstance(uptime, list)
        # Check structure if any data exists
        if uptime:
            day_data = uptime[0]
            assert "date" in day_data
            assert "total_plays" in day_data
            assert "successful_plays" in day_data
            assert "uptime_percent" in day_data
            assert "total_hours" in day_data

    def test_get_error_timeline_empty(self, test_analytics):
        """Test getting error timeline from empty database."""
        timeline = test_analytics.get_error_timeline(days=7)

        assert timeline == []

    def test_get_error_timeline_with_data(self, test_analytics, populated_database):
        """Test getting error timeline with populated database."""
        timeline = test_analytics.get_error_timeline(days=30)

        assert isinstance(timeline, list)
        # Check structure if any errors exist
        if timeline:
            error = timeline[0]
            assert "id" in error
            assert "timestamp" in error
            assert "service" in error
            assert "severity" in error
            assert "message" in error

    def test_get_error_timeline_filtered_by_severity(self, test_analytics, populated_database):
        """Test getting error timeline filtered by severity."""
        timeline = test_analytics.get_error_timeline(days=30, severity="error")

        assert isinstance(timeline, list)
        # All errors should have 'error' severity
        for error in timeline:
            assert error["severity"] == "error"

    def test_context_manager(self, test_config):
        """Test Analytics as context manager."""
        with Analytics(test_config) as analytics:
            assert analytics is not None
            assert analytics.engine is not None

    def test_close(self, test_analytics):
        """Test closing analytics."""
        test_analytics.close()
        # Should not raise exception


class TestAnalyticsEdgeCases:
    """Test edge cases for Analytics class."""

    def test_get_play_stats_future_dates(self, test_analytics):
        """Test getting stats with future dates."""
        start_date = datetime.now() + timedelta(days=1)
        end_date = datetime.now() + timedelta(days=7)

        stats = test_analytics.get_play_stats(start_date=start_date, end_date=end_date)

        # Should return zero stats
        assert stats["total_plays"] == 0

    def test_get_play_stats_reversed_dates(self, test_analytics):
        """Test getting stats with reversed date range."""
        # This should still work, just return no results
        start_date = datetime.now()
        end_date = datetime.now() - timedelta(days=7)

        stats = test_analytics.get_play_stats(start_date=start_date, end_date=end_date)

        assert stats["total_plays"] == 0

    def test_get_most_played_tracks_zero_limit(self, test_analytics, populated_database):
        """Test getting most played tracks with zero limit."""
        tracks = test_analytics.get_most_played_tracks(days=7, limit=0)

        assert tracks == []

    def test_get_track_history_case_insensitive(self, test_analytics, populated_database):
        """Test track history lookup is case insensitive."""
        history1 = test_analytics.get_track_history("Artist 0", "Song 0")
        history2 = test_analytics.get_track_history("ARTIST 0", "SONG 0")

        # Should return same results (normalized internally)
        assert len(history1) == len(history2)


class TestAnalyticsIntegration:
    """Integration tests for Analytics."""

    def test_full_analytics_workflow(self, test_analytics, test_logger, sample_track_info):
        """Test complete analytics workflow."""
        # Log some tracks
        for i in range(5):
            play_id = test_logger.log_track_started(
                {
                    "artist": f"Artist {i % 2}",
                    "title": f"Song {i % 3}",
                    "album": "Test Album",
                    "duration": 180,
                },
                f"/srv/loops/track{i}.mp4",
                12345 + i,
            )

            # Log some errors
            if i % 2 == 0:
                test_logger.log_error("ffmpeg", "warning", f"Warning {i}")

            test_logger.log_track_ended(play_id)

        # Get analytics
        stats = test_analytics.get_play_stats(days=1)
        assert stats["total_plays"] == 5

        most_played = test_analytics.get_most_played_tracks(days=1)
        assert len(most_played) > 0

        errors = test_analytics.get_error_summary(days=1)
        assert len(errors) > 0

    def test_daily_and_weekly_summaries(self, test_analytics, test_logger):
        """Test daily and weekly summary generation."""
        # Log a track
        play_id = test_logger.log_track_started(
            {"artist": "Test Artist", "title": "Test Song", "duration": 180},
            "/srv/loops/test.mp4",
            12345,
        )
        test_logger.log_track_ended(play_id)

        # Get summaries
        daily = test_analytics.get_daily_summary()
        assert daily is not None

        weekly = test_analytics.get_weekly_summary()
        assert weekly is not None
