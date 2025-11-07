"""
Integration demonstration: FFmpeg Manager with Track Mapper (SHARD-3).

This script demonstrates how SHARD-4 (FFmpeg Manager) integrates with
SHARD-3 (Track Mapper) to stream video loops for tracks.

Usage:
    python -m ffmpeg_manager.examples.integration_demo
"""

import asyncio
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Demonstrate integration between FFmpeg Manager and Track Mapper."""

    # Import modules
    try:
        from ffmpeg_manager import FFmpegProcessManager, FFmpegConfig, EncodingPreset
        from track_mapper import TrackMapper, TrackMapperConfig
    except ImportError as e:
        logger.error(f"Failed to import modules: {e}")
        logger.info("Make sure both ffmpeg_manager and track_mapper are installed")
        return

    logger.info("=" * 60)
    logger.info("FFmpeg Manager + Track Mapper Integration Demo")
    logger.info("=" * 60)

    # 1. Initialize Track Mapper (SHARD-3)
    logger.info("\n1. Initializing Track Mapper (SHARD-3)...")
    try:
        track_config = TrackMapperConfig.from_env()
        track_mapper = TrackMapper(track_config)
        logger.info("✅ Track Mapper initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Track Mapper: {e}")
        logger.info("This is expected if database is not running")
        logger.info("The integration flow would work as follows:")
        demonstrate_integration_flow()
        return

    # 2. Initialize FFmpeg Manager (SHARD-4)
    logger.info("\n2. Initializing FFmpeg Manager (SHARD-4)...")
    ffmpeg_config = FFmpegConfig(
        encoding_preset=EncodingPreset.PRESET_480P_TEST,  # Low quality for testing
        fade_in_duration=1.0,
        overlap_duration=2.0,
    )
    ffmpeg_manager = FFmpegProcessManager(config=ffmpeg_config)
    logger.info("✅ FFmpeg Manager initialized")

    # 3. Simulate track change workflow
    logger.info("\n3. Simulating track change workflow...")

    # Example track metadata (as would come from AzuraCast webhook)
    track_info = {
        "artist": "Example Artist",
        "title": "Example Song",
        "song_id": "123",
        "album": "Example Album",
    }

    logger.info(f"   Track: {track_info['artist']} - {track_info['title']}")

    # Step 1: Get loop path from Track Mapper
    logger.info("\n   Step 1: Query Track Mapper for video loop...")
    try:
        loop_path = track_mapper.get_loop(
            artist=track_info["artist"],
            title=track_info["title"],
            song_id=track_info.get("song_id"),
        )
        logger.info(f"   ✅ Got loop path: {loop_path}")
    except Exception as e:
        logger.error(f"   ❌ Failed to get loop: {e}")
        loop_path = "/srv/loops/default.mp4"
        logger.info(f"   Using fallback: {loop_path}")

    # Step 2: Build FFmpeg command
    logger.info("\n   Step 2: Build FFmpeg command...")
    cmd = ffmpeg_manager.command_builder.build_command(loop_path=loop_path, fade_in=True)
    logger.info(f"   ✅ Command built: {' '.join(cmd[:5])}...")

    # Step 3: Start/switch stream (simulated - not actually spawning FFmpeg)
    logger.info("\n   Step 3: Stream management (simulated)...")
    logger.info("   Would call: await ffmpeg_manager.switch_track(loop_path)")
    logger.info("   This would:")
    logger.info("     - Spawn new FFmpeg process with the loop")
    logger.info("     - Wait for overlap duration (2.0s)")
    logger.info("     - Terminate old process gracefully")
    logger.info("     - Monitor new process for health")

    # 4. Show integration points
    logger.info("\n4. Integration Points Summary:")
    logger.info("   SHARD-2 (Metadata Watcher) →")
    logger.info("   SHARD-3 (Track Mapper) → get_loop() →")
    logger.info("   SHARD-4 (FFmpeg Manager) → switch_track() →")
    logger.info("   SHARD-1 (nginx-rtmp) → YouTube")

    # 5. Cleanup
    logger.info("\n5. Cleanup...")
    await ffmpeg_manager.cleanup()
    track_mapper.close()
    logger.info("✅ Cleanup complete")

    logger.info("\n" + "=" * 60)
    logger.info("Integration demo completed successfully!")
    logger.info("=" * 60)


def demonstrate_integration_flow():
    """Demonstrate integration flow when database is not available."""
    logger.info("\n📋 Integration Flow (Conceptual):")
    logger.info("")
    logger.info("1. AzuraCast sends webhook to Metadata Watcher:")
    logger.info("   POST /webhook/azuracast")
    logger.info("   {")
    logger.info('     "song": {"artist": "Artist", "title": "Title", "id": "123"}')
    logger.info("   }")
    logger.info("")
    logger.info("2. Metadata Watcher queries Track Mapper:")
    logger.info("   from track_mapper import TrackMapper")
    logger.info("   loop_path = mapper.get_loop('Artist', 'Title', song_id='123')")
    logger.info("   # Returns: /srv/loops/tracks/artist_-_title.mp4")
    logger.info("")
    logger.info("3. Metadata Watcher calls FFmpeg Manager:")
    logger.info("   from ffmpeg_manager import FFmpegProcessManager")
    logger.info("   success = await manager.switch_track(loop_path)")
    logger.info("")
    logger.info("4. FFmpeg Manager executes graceful handover:")
    logger.info("   - Spawns new FFmpeg process with new loop")
    logger.info("   - Applies fade-in transition")
    logger.info("   - Waits for overlap duration (2s)")
    logger.info("   - Terminates old process")
    logger.info("   - Monitors new process for errors")
    logger.info("")
    logger.info("5. FFmpeg streams to nginx-rtmp (SHARD-1):")
    logger.info("   rtmp://nginx-rtmp:1935/live/stream")
    logger.info("")
    logger.info("6. nginx-rtmp relays to YouTube:")
    logger.info("   rtmp://a.rtmp.youtube.com/live2/<stream_key>")
    logger.info("")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\n\nFatal error: {e}", exc_info=True)
        sys.exit(1)
