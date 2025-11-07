"""Unit tests for TrackMapper class"""

import os
import tempfile
from datetime import datetime
from unittest.mock import Mock, patch
import pytest

from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from track_mapper.config import TrackMapperConfig
from track_mapper.mapper import TrackMapper


@pytest.fixture
def temp_loop_file():
    """Create a temporary loop file for testing"""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        f.write(b"fake mp4 content")
        temp_path = f.name

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def mock_config(temp_loop_file):
    """Create a mock configuration for testing"""
    config = TrackMapperConfig(
        postgres_host="localhost",
        postgres_port=5432,
        postgres_user="test",
        postgres_password="test",
        postgres_db="test_db",
        loops_path="/tmp/loops",
        default_loop=temp_loop_file,
        cache_size=10,
        cache_ttl_seconds=3600,
    )
    return config


@pytest.fixture
def mock_engine():
    """Create a mock SQLAlchemy engine"""
    engine = Mock()
    connection = Mock()

    # Setup connection context manager
    connection.__enter__ = Mock(return_value=connection)
    connection.__exit__ = Mock(return_value=False)
    engine.connect = Mock(return_value=connection)

    return engine


@pytest.fixture
def mapper(mock_config, mock_engine):
    """Create a TrackMapper with mocked database"""
    with patch("track_mapper.mapper.create_engine", return_value=mock_engine):
        mapper = TrackMapper(mock_config)
        yield mapper
        mapper.close()


class TestTrackMapper:
    """Test TrackMapper class"""

    def test_initialization(self, mock_config, mock_engine):
        """Test TrackMapper initialization"""
        with patch("track_mapper.mapper.create_engine", return_value=mock_engine):
            mapper = TrackMapper(mock_config)

            assert mapper.config == mock_config
            assert mapper.engine == mock_engine
            assert mapper._cache_max_size == 10
            assert mapper._cache_ttl == 3600
            assert len(mapper._cache) == 0

    def test_initialization_invalid_config(self):
        """Test initialization with invalid config"""
        config = TrackMapperConfig(postgres_password="")  # Invalid

        with pytest.raises(ValueError):
            TrackMapper(config)

    def test_normalize_track_key(self):
        """Test track key normalization"""
        assert (
            TrackMapper.normalize_track_key("The Beatles", "Hey Jude") == "the beatles - hey jude"
        )
        assert TrackMapper.normalize_track_key("  Artist  ", "  Title  ") == "artist - title"
        assert TrackMapper.normalize_track_key("UPPERCASE", "TITLE") == "uppercase - title"

    def test_get_loop_from_cache(self, mapper, temp_loop_file):
        """Test getting loop from cache"""
        track_key = "artist - title"

        # Add to cache
        mapper._add_to_cache(track_key, temp_loop_file)

        # Should return from cache
        result = mapper.get_loop("Artist", "Title")
        assert result == temp_loop_file

    def test_get_loop_from_database(self, mapper, mock_engine, temp_loop_file):
        """Test getting loop from database when not in cache"""
        track_key = "artist - title"

        # Mock database response
        mock_result = Mock()
        mock_result.fetchone = Mock(return_value=(temp_loop_file,))
        mock_engine.connect.return_value.__enter__.return_value.execute = Mock(
            return_value=mock_result
        )

        # Get loop
        with patch.object(mapper, "_increment_play_count_async"):
            result = mapper.get_loop("Artist", "Title")

        assert result == temp_loop_file
        assert track_key in mapper._cache

    def test_get_loop_fallback_to_default(self, mapper, mock_engine, temp_loop_file):
        """Test fallback to default loop when track not found"""
        # Mock database returning None
        mock_result = Mock()
        mock_result.fetchone = Mock(return_value=None)
        mock_engine.connect.return_value.__enter__.return_value.execute = Mock(
            return_value=mock_result
        )

        # Should return default loop
        result = mapper.get_loop("Unknown Artist", "Unknown Title")
        assert result == temp_loop_file

    def test_get_loop_cache_expired(self, mapper, temp_loop_file):
        """Test cache expiration"""
        track_key = "artist - title"

        # Add to cache with old timestamp
        old_timestamp = datetime.now().timestamp() - 7200  # 2 hours ago
        mapper._cache[track_key] = (temp_loop_file, old_timestamp)

        # Mock database response
        mock_result = Mock()
        mock_result.fetchone = Mock(return_value=(temp_loop_file,))
        mapper.engine.connect.return_value.__enter__.return_value.execute = Mock(
            return_value=mock_result
        )

        # Should query database due to expired cache
        with patch.object(mapper, "_increment_play_count_async"):
            result = mapper.get_loop("Artist", "Title")

        assert result == temp_loop_file

    def test_add_mapping_success(self, mapper, mock_engine, temp_loop_file):
        """Test adding a new mapping"""
        track_key = "artist - title"

        # Mock successful insert
        mock_engine.connect.return_value.__enter__.return_value.execute = Mock()

        result = mapper.add_mapping(track_key, temp_loop_file, "123", "Test note")

        assert result is True
        assert track_key in mapper._cache

    def test_add_mapping_already_exists(self, mapper, mock_engine, temp_loop_file):
        """Test adding a mapping that already exists"""
        track_key = "artist - title"

        # Mock IntegrityError (duplicate key)
        mock_engine.connect.return_value.__enter__.return_value.execute = Mock(
            side_effect=IntegrityError("", "", "")
        )

        result = mapper.add_mapping(track_key, temp_loop_file)

        assert result is False

    def test_add_mapping_invalid_file(self, mapper):
        """Test adding mapping with non-existent file"""
        track_key = "artist - title"

        with pytest.raises(ValueError, match="does not exist"):
            mapper.add_mapping(track_key, "/nonexistent/file.mp4")

    def test_update_mapping_success(self, mapper, mock_engine, temp_loop_file):
        """Test updating an existing mapping"""
        track_key = "artist - title"

        # Mock successful update
        mock_result = Mock()
        mock_result.rowcount = 1
        mock_engine.connect.return_value.__enter__.return_value.execute = Mock(
            return_value=mock_result
        )

        result = mapper.update_mapping(track_key, temp_loop_file, "456", "Updated")

        assert result is True
        assert track_key in mapper._cache

    def test_update_mapping_not_found(self, mapper, mock_engine, temp_loop_file):
        """Test updating a non-existent mapping"""
        track_key = "artist - title"

        # Mock no rows updated
        mock_result = Mock()
        mock_result.rowcount = 0
        mock_engine.connect.return_value.__enter__.return_value.execute = Mock(
            return_value=mock_result
        )

        result = mapper.update_mapping(track_key, temp_loop_file)

        assert result is False

    def test_update_mapping_invalid_file(self, mapper):
        """Test updating mapping with non-existent file"""
        track_key = "artist - title"

        with pytest.raises(ValueError, match="does not exist"):
            mapper.update_mapping(track_key, "/nonexistent/file.mp4")

    def test_delete_mapping_success(self, mapper, mock_engine):
        """Test soft deleting a mapping"""
        track_key = "artist - title"

        # Add to cache first
        mapper._cache[track_key] = ("/path/to/file.mp4", datetime.now().timestamp())

        # Mock successful delete
        mock_result = Mock()
        mock_result.rowcount = 1
        mock_engine.connect.return_value.__enter__.return_value.execute = Mock(
            return_value=mock_result
        )

        result = mapper.delete_mapping(track_key)

        assert result is True
        assert track_key not in mapper._cache

    def test_delete_mapping_not_found(self, mapper, mock_engine):
        """Test deleting a non-existent mapping"""
        track_key = "artist - title"

        # Mock no rows deleted
        mock_result = Mock()
        mock_result.rowcount = 0
        mock_engine.connect.return_value.__enter__.return_value.execute = Mock(
            return_value=mock_result
        )

        result = mapper.delete_mapping(track_key)

        assert result is False

    def test_increment_play_count(self, mapper, mock_engine):
        """Test incrementing play count"""
        track_key = "artist - title"

        # Mock successful update
        mock_engine.connect.return_value.__enter__.return_value.execute = Mock()

        # Should not raise
        mapper.increment_play_count(track_key)

    def test_increment_play_count_error(self, mapper, mock_engine):
        """Test play count increment handles errors gracefully"""
        track_key = "artist - title"

        # Mock database error
        mock_engine.connect.return_value.__enter__.return_value.execute = Mock(
            side_effect=SQLAlchemyError("DB error")
        )

        # Should not raise (just log error)
        mapper.increment_play_count(track_key)

    def test_get_default_loop_from_db(self, mapper, mock_engine, temp_loop_file):
        """Test getting default loop from database"""
        # Mock database response
        mock_result = Mock()
        mock_result.fetchone = Mock(return_value=(temp_loop_file,))
        mock_engine.connect.return_value.__enter__.return_value.execute = Mock(
            return_value=mock_result
        )

        result = mapper.get_default_loop()
        assert result == temp_loop_file

    def test_get_default_loop_from_config(self, mapper, mock_engine, temp_loop_file):
        """Test fallback to config when database query fails"""
        # Mock database error
        mock_engine.connect.return_value.__enter__.return_value.execute = Mock(
            side_effect=SQLAlchemyError("DB error")
        )

        result = mapper.get_default_loop()
        assert result == temp_loop_file

    def test_get_default_loop_not_found(self, mapper, mock_engine):
        """Test error when default loop doesn't exist"""
        # Mock returning non-existent path
        mock_result = Mock()
        mock_result.fetchone = Mock(return_value=("/nonexistent.mp4",))
        mock_engine.connect.return_value.__enter__.return_value.execute = Mock(
            return_value=mock_result
        )

        with pytest.raises(FileNotFoundError):
            mapper.get_default_loop()

    def test_get_stats(self, mapper, mock_engine):
        """Test getting statistics"""
        # Mock database response
        mock_result = Mock()
        mock_result.fetchone = Mock(return_value=(100, 95, 5000, 50.0, "top track"))
        mock_engine.connect.return_value.__enter__.return_value.execute = Mock(
            return_value=mock_result
        )

        stats = mapper.get_stats()

        assert stats["total_tracks"] == 100
        assert stats["active_tracks"] == 95
        assert stats["total_plays"] == 5000
        assert stats["avg_plays_per_track"] == 50.0
        assert stats["most_played_track"] == "top track"

    def test_get_stats_error(self, mapper, mock_engine):
        """Test statistics returns zeros on error"""
        # Mock database error
        mock_engine.connect.return_value.__enter__.return_value.execute = Mock(
            side_effect=SQLAlchemyError("DB error")
        )

        stats = mapper.get_stats()

        assert stats["total_tracks"] == 0
        assert stats["active_tracks"] == 0

    def test_get_all_mappings(self, mapper, mock_engine):
        """Test getting all mappings"""
        # Mock database response
        mock_result = Mock()
        mock_result.__iter__ = Mock(
            return_value=iter(
                [
                    (1, "track1", "123", "/path1.mp4", None, None, 10, None, True, None),
                    (2, "track2", "456", "/path2.mp4", None, None, 20, None, True, None),
                ]
            )
        )
        mock_engine.connect.return_value.__enter__.return_value.execute = Mock(
            return_value=mock_result
        )

        mappings = mapper.get_all_mappings()

        assert len(mappings) == 2
        assert mappings[0]["track_key"] == "track1"
        assert mappings[1]["play_count"] == 20

    def test_get_all_mappings_with_limit(self, mapper, mock_engine):
        """Test getting mappings with limit"""
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([]))
        mock_execute = Mock(return_value=mock_result)
        mock_engine.connect.return_value.__enter__.return_value.execute = mock_execute

        mapper.get_all_mappings(active_only=False, limit=50)

        # Verify LIMIT was added to query
        call_args = mock_execute.call_args[0][0]
        assert "LIMIT 50" in str(call_args)

    def test_cache_management(self, mapper, temp_loop_file):
        """Test cache add/get/remove operations"""
        track_key = "artist - title"

        # Add to cache
        mapper._add_to_cache(track_key, temp_loop_file)
        assert len(mapper._cache) == 1

        # Get from cache
        cached = mapper._get_from_cache(track_key)
        assert cached == temp_loop_file

        # Remove from cache
        mapper._remove_from_cache(track_key)
        assert len(mapper._cache) == 0

    def test_cache_eviction(self, mapper, temp_loop_file):
        """Test LRU cache eviction when full"""
        # Fill cache to max
        for i in range(mapper._cache_max_size):
            mapper._add_to_cache(f"track{i}", temp_loop_file)

        assert len(mapper._cache) == mapper._cache_max_size

        # Add one more, should evict oldest
        mapper._add_to_cache("new_track", temp_loop_file)
        assert len(mapper._cache) == mapper._cache_max_size

    def test_clear_cache(self, mapper, temp_loop_file):
        """Test clearing cache"""
        mapper._add_to_cache("track1", temp_loop_file)
        mapper._add_to_cache("track2", temp_loop_file)

        assert len(mapper._cache) > 0

        mapper.clear_cache()
        assert len(mapper._cache) == 0

    def test_get_cache_stats(self, mapper, temp_loop_file):
        """Test cache statistics"""
        mapper._add_to_cache("track1", temp_loop_file)
        mapper._add_to_cache("track2", temp_loop_file)

        stats = mapper.get_cache_stats()

        assert stats["size"] == 2
        assert stats["max_size"] == 10
        assert stats["ttl_seconds"] == 3600

    def test_validate_file(self, temp_loop_file):
        """Test file validation"""
        # Valid file
        assert TrackMapper._validate_file(temp_loop_file) is True

        # Non-existent file
        assert TrackMapper._validate_file("/nonexistent/file.mp4") is False

        # Directory (not a file)
        assert TrackMapper._validate_file("/tmp") is False

    def test_context_manager(self, mock_config, mock_engine):
        """Test using TrackMapper as context manager"""
        with patch("track_mapper.mapper.create_engine", return_value=mock_engine):
            with TrackMapper(mock_config) as mapper:
                assert mapper.engine == mock_engine

            # Should have called dispose
            mock_engine.dispose.assert_called_once()

    def test_repr(self, mapper):
        """Test string representation"""
        repr_str = repr(mapper)
        assert "TrackMapper" in repr_str
        assert "test_db" in repr_str

    def test_query_loop_path_by_song_id(self, mapper, mock_engine, temp_loop_file):
        """Test querying loop path by song ID when track key not found"""
        track_key = "artist - title"
        song_id = "123"

        # Mock: first query (track_key) returns None, second query (song_id) returns path
        mock_result1 = Mock()
        mock_result1.fetchone = Mock(return_value=None)
        mock_result2 = Mock()
        mock_result2.fetchone = Mock(return_value=(temp_loop_file,))

        mock_execute = Mock(side_effect=[mock_result1, mock_result2])
        mock_engine.connect.return_value.__enter__.return_value.execute = mock_execute

        result = mapper._query_loop_path(track_key, song_id)
        assert result == temp_loop_file

    def test_get_loop_with_invalid_cached_path(self, mapper, mock_engine, temp_loop_file):
        """Test that invalid cached paths are removed"""
        track_key = "artist - title"

        # Add invalid path to cache
        mapper._add_to_cache(track_key, "/nonexistent/file.mp4")

        # Mock database response
        mock_result = Mock()
        mock_result.fetchone = Mock(return_value=(temp_loop_file,))
        mock_engine.connect.return_value.__enter__.return_value.execute = Mock(
            return_value=mock_result
        )

        with patch.object(mapper, "_increment_play_count_async"):
            result = mapper.get_loop("Artist", "Title")

        # Should have queried database and returned valid path
        assert result == temp_loop_file
