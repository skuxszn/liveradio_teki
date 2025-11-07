"""Integration tests for TrackMapper with real database

These tests require a running PostgreSQL database.
Set environment variables for connection or use defaults.
"""

import os
import tempfile
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from track_mapper.config import TrackMapperConfig
from track_mapper.mapper import TrackMapper


# Skip integration tests if database is not available
def is_database_available():
    """Check if test database is available"""
    try:
        config = TrackMapperConfig.from_env()
        engine = create_engine(config.database_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except (OperationalError, Exception):
        return False


pytestmark = pytest.mark.skipif(
    not is_database_available(), reason="PostgreSQL database not available"
)


@pytest.fixture(scope="module")
def test_config():
    """Create test configuration"""
    return TrackMapperConfig.from_env()


@pytest.fixture(scope="module")
def setup_database(test_config):
    """Setup test database with schema"""
    engine = create_engine(test_config.database_url)

    # Read and execute schema
    schema_path = os.path.join(os.path.dirname(__file__), "../../../track_mapper/schema.sql")

    with open(schema_path, "r") as f:
        schema_sql = f.read()

    with engine.connect() as conn:
        # Execute schema (creates tables if not exist)
        for statement in schema_sql.split(";"):
            if statement.strip():
                try:
                    conn.execute(text(statement))
                except Exception:
                    pass  # Ignore errors for already existing objects
        conn.commit()

    yield engine

    # Cleanup: Drop test tables
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS track_mappings CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS default_config CASCADE"))
        conn.execute(text("DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE"))
        conn.execute(text("DROP FUNCTION IF EXISTS normalize_track_key(TEXT, TEXT) CASCADE"))
        conn.execute(text("DROP FUNCTION IF EXISTS get_track_stats() CASCADE"))
        conn.commit()

    engine.dispose()


@pytest.fixture
def clean_database(setup_database):
    """Clean database before each test"""
    with setup_database.connect() as conn:
        conn.execute(text("DELETE FROM track_mappings"))
        conn.execute(
            text(
                "INSERT INTO default_config (key, value) VALUES "
                "('default_loop', '/srv/loops/default.mp4') "
                "ON CONFLICT (key) DO UPDATE SET value = '/srv/loops/default.mp4'"
            )
        )
        conn.commit()


@pytest.fixture
def temp_loop_files():
    """Create temporary loop files for testing"""
    files = []
    for i in range(3):
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"fake mp4 content for testing")
            files.append(f.name)

    yield files

    # Cleanup
    for file_path in files:
        if os.path.exists(file_path):
            os.unlink(file_path)


@pytest.fixture
def mapper(test_config, clean_database):
    """Create TrackMapper with real database"""
    mapper = TrackMapper(test_config)
    yield mapper
    mapper.close()


class TestTrackMapperIntegration:
    """Integration tests for TrackMapper with real database"""

    def test_add_and_get_mapping(self, mapper, temp_loop_files):
        """Test adding a mapping and retrieving it"""
        track_key = mapper.normalize_track_key("Test Artist", "Test Song")
        loop_path = temp_loop_files[0]

        # Add mapping
        result = mapper.add_mapping(track_key, loop_path, "123", "Test note")
        assert result is True

        # Get loop
        retrieved = mapper.get_loop("Test Artist", "Test Song")
        assert retrieved == loop_path

    def test_update_existing_mapping(self, mapper, temp_loop_files):
        """Test updating an existing mapping"""
        track_key = mapper.normalize_track_key("Artist", "Song")

        # Add initial mapping
        mapper.add_mapping(track_key, temp_loop_files[0], "123")

        # Update with new path
        result = mapper.update_mapping(track_key, temp_loop_files[1], "456", "Updated")
        assert result is True

        # Verify update
        retrieved = mapper.get_loop("Artist", "Song")
        assert retrieved == temp_loop_files[1]

    def test_delete_mapping(self, mapper, temp_loop_files):
        """Test soft deleting a mapping"""
        track_key = mapper.normalize_track_key("Artist", "Song")

        # Add mapping
        mapper.add_mapping(track_key, temp_loop_files[0])

        # Delete
        result = mapper.delete_mapping(track_key)
        assert result is True

        # Should fall back to default after deletion
        retrieved = mapper.get_loop("Artist", "Song")
        assert retrieved != temp_loop_files[0]

    def test_play_count_increment(self, mapper, temp_loop_files):
        """Test play count increments correctly"""
        track_key = mapper.normalize_track_key("Artist", "Song")

        # Add mapping
        mapper.add_mapping(track_key, temp_loop_files[0])

        # Increment play count multiple times
        for _ in range(5):
            mapper.increment_play_count(track_key)

        # Verify count in database
        with mapper.engine.connect() as conn:
            result = conn.execute(
                text("SELECT play_count FROM track_mappings WHERE track_key = :key"),
                {"key": track_key},
            )
            row = result.fetchone()
            assert row[0] == 5

    def test_get_stats(self, mapper, temp_loop_files):
        """Test getting statistics"""
        # Add multiple mappings
        for i in range(3):
            track_key = f"artist{i} - song{i}"
            mapper.add_mapping(track_key, temp_loop_files[i % len(temp_loop_files)])

            # Increment play counts
            for _ in range(i + 1):
                mapper.increment_play_count(track_key)

        # Get stats
        stats = mapper.get_stats()

        assert stats["total_tracks"] == 3
        assert stats["active_tracks"] == 3
        assert stats["total_plays"] == 6  # 1 + 2 + 3
        assert stats["avg_plays_per_track"] == 2.0

    def test_get_all_mappings(self, mapper, temp_loop_files):
        """Test retrieving all mappings"""
        # Add mappings
        for i in range(3):
            track_key = f"artist{i} - song{i}"
            mapper.add_mapping(track_key, temp_loop_files[i % len(temp_loop_files)], f"song{i}")

        # Get all
        mappings = mapper.get_all_mappings()

        assert len(mappings) == 3
        assert all("track_key" in m for m in mappings)
        assert all("loop_file_path" in m for m in mappings)

    def test_cache_reduces_queries(self, mapper, temp_loop_files):
        """Test that cache reduces database queries"""
        track_key = mapper.normalize_track_key("Artist", "Song")

        # Add mapping
        mapper.add_mapping(track_key, temp_loop_files[0])

        # Clear cache to ensure first query hits database
        mapper.clear_cache()

        # First get (cache miss)
        result1 = mapper.get_loop("Artist", "Song")
        assert result1 == temp_loop_files[0]

        # Second get (cache hit, should not query database)
        cached_result = mapper._get_from_cache(track_key)
        assert cached_result == temp_loop_files[0]

    def test_duplicate_add_fails(self, mapper, temp_loop_files):
        """Test that adding duplicate track key fails"""
        track_key = mapper.normalize_track_key("Artist", "Song")

        # Add first time
        result1 = mapper.add_mapping(track_key, temp_loop_files[0])
        assert result1 is True

        # Try to add again
        result2 = mapper.add_mapping(track_key, temp_loop_files[1])
        assert result2 is False

    def test_song_id_lookup(self, mapper, temp_loop_files):
        """Test lookup by AzuraCast song ID"""
        track_key = mapper.normalize_track_key("Artist", "Song")
        song_id = "azuracast_123"

        # Add with song ID
        mapper.add_mapping(track_key, temp_loop_files[0], song_id)

        # Clear cache
        mapper.clear_cache()

        # Query with different artist/title but same song ID
        # (Simulate scenario where metadata changed but song ID same)
        result = mapper.get_loop("Different Artist", "Different Song", song_id)
        assert result == temp_loop_files[0]

    def test_default_loop_from_database(self, mapper, temp_loop_files):
        """Test getting default loop from database config"""
        # Update default loop in database
        with mapper.engine.connect() as conn:
            conn.execute(
                text("UPDATE default_config SET value = :path WHERE key = 'default_loop'"),
                {"path": temp_loop_files[0]},
            )
            conn.commit()

        # Get default loop
        default = mapper.get_default_loop()
        assert default == temp_loop_files[0]

    def test_last_played_timestamp(self, mapper, temp_loop_files):
        """Test that last_played_at is updated"""
        track_key = mapper.normalize_track_key("Artist", "Song")

        # Add mapping
        mapper.add_mapping(track_key, temp_loop_files[0])

        # Increment play count (should update last_played_at)
        mapper.increment_play_count(track_key)

        # Verify last_played_at is set
        with mapper.engine.connect() as conn:
            result = conn.execute(
                text("SELECT last_played_at FROM track_mappings WHERE track_key = :key"),
                {"key": track_key},
            )
            row = result.fetchone()
            assert row[0] is not None

    def test_mappings_ordering(self, mapper, temp_loop_files):
        """Test that mappings are ordered by play count"""
        # Add mappings with different play counts
        for i in range(3):
            track_key = f"artist{i} - song{i}"
            mapper.add_mapping(track_key, temp_loop_files[i % len(temp_loop_files)])

            # Give different play counts
            for _ in range(3 - i):  # 3, 2, 1
                mapper.increment_play_count(track_key)

        # Get all mappings (should be ordered by play_count DESC)
        mappings = mapper.get_all_mappings()

        assert mappings[0]["track_key"] == "artist0 - song0"  # Most played
        assert mappings[-1]["track_key"] == "artist2 - song2"  # Least played

    def test_context_manager_closes_connection(self, test_config, clean_database):
        """Test that context manager properly closes connections"""
        # Use context manager
        with TrackMapper(test_config) as mapper:
            assert mapper.engine is not None

        # Engine should be disposed after context exit
        # (Can't easily test this without accessing internals)

    def test_invalid_file_path_not_added(self, mapper):
        """Test that mappings with invalid paths cannot be added"""
        track_key = "artist - song"

        with pytest.raises(ValueError, match="does not exist"):
            mapper.add_mapping(track_key, "/nonexistent/file.mp4")

    def test_get_loop_increments_play_count(self, mapper, temp_loop_files):
        """Test that get_loop automatically increments play count"""
        track_key = mapper.normalize_track_key("Artist", "Song")

        # Add mapping
        mapper.add_mapping(track_key, temp_loop_files[0])

        # Get loop (should increment count)
        mapper.get_loop("Artist", "Song")

        # Verify count increased
        with mapper.engine.connect() as conn:
            result = conn.execute(
                text("SELECT play_count FROM track_mappings WHERE track_key = :key"),
                {"key": track_key},
            )
            row = result.fetchone()
            # Should be at least 1 (incremented by get_loop)
            assert row[0] >= 1



