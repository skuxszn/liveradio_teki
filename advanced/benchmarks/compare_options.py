"""Benchmark comparison between Option A and Option B.

This script compares the performance and gap duration between:
- Option A: Persistent FFmpeg with dual-input crossfade
- Option B: Spawn-per-track FFmpeg (SHARD-4 implementation)

Metrics:
- Track switch gap duration (audio/video discontinuity)
- CPU usage
- Memory usage
- Process restart time
- Resource stability over time
"""

import asyncio
import logging
import os
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import psutil

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Module imports after path modification (intentional)  # noqa: E402
from advanced.config import AdvancedConfig  # noqa: E402
from advanced.dual_input_ffmpeg import DualInputFFmpegManager  # noqa: E402
from ffmpeg_manager.process_manager import FFmpegProcessManager  # noqa: E402
from ffmpeg_manager.config import get_config as get_ffmpeg_config  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Results from a benchmark run."""

    option_name: str
    switch_count: int
    total_duration_seconds: float

    # Gap metrics
    avg_gap_ms: float
    min_gap_ms: float
    max_gap_ms: float
    std_gap_ms: float

    # Resource metrics
    avg_cpu_percent: float
    max_cpu_percent: float
    avg_memory_mb: float
    max_memory_mb: float

    # Stability metrics
    crash_count: int
    restart_count: int
    errors: List[str]


class BenchmarkRunner:
    """Runs benchmarks for Option A and Option B."""

    def __init__(
        self,
        test_loops: List[str],
        iterations: int = 10,
        measure_duration: int = 60,
    ):
        """Initialize benchmark runner.

        Args:
            test_loops: List of video loop file paths for testing
            iterations: Number of track switches to perform
            measure_duration: Total duration to measure in seconds
        """
        self.test_loops = test_loops
        self.iterations = iterations
        self.measure_duration = measure_duration

        # Results
        self.option_a_result: Optional[BenchmarkResult] = None
        self.option_b_result: Optional[BenchmarkResult] = None

    async def run_option_a_benchmark(self) -> BenchmarkResult:
        """Benchmark Option A (dual-input persistent FFmpeg).

        Returns:
            BenchmarkResult for Option A
        """
        logger.info("=" * 60)
        logger.info("Running Option A Benchmark (Persistent FFmpeg)")
        logger.info("=" * 60)

        config = AdvancedConfig.from_env()
        config.crossfade_duration = 2.0

        manager = DualInputFFmpegManager(config)

        gap_times_ms = []
        cpu_samples = []
        memory_samples = []
        errors = []
        crash_count = 0
        restart_count = 0

        try:
            # Start initial stream
            logger.info("Starting initial stream...")
            success = await manager.start_stream(self.test_loops[0])
            if not success:
                raise RuntimeError("Failed to start Option A stream")

            start_time = time.time()

            # Perform track switches
            for i in range(self.iterations):
                loop_idx = (i + 1) % len(self.test_loops)
                new_loop = self.test_loops[loop_idx]

                logger.info(f"Switch {i+1}/{self.iterations}: {new_loop}")

                # Measure gap time
                switch_start = time.time()
                success = await manager.switch_track(new_loop)
                switch_end = time.time()

                if success:
                    gap_ms = (switch_end - switch_start) * 1000
                    gap_times_ms.append(gap_ms)
                    logger.info(f"  Gap: {gap_ms:.2f}ms")
                else:
                    errors.append(f"Switch {i+1} failed")
                    crash_count += 1

                # Sample resource usage
                if manager._process and manager._process.poll() is None:
                    try:
                        proc = psutil.Process(manager._process.pid)
                        cpu_samples.append(proc.cpu_percent(interval=0.1))
                        memory_samples.append(proc.memory_info().rss / 1024 / 1024)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

                # Small delay between switches
                await asyncio.sleep(2)

            total_duration = time.time() - start_time

            # Stop stream
            await manager.stop_stream()

            # Calculate metrics
            result = BenchmarkResult(
                option_name="Option A (Persistent FFmpeg)",
                switch_count=len(gap_times_ms),
                total_duration_seconds=total_duration,
                avg_gap_ms=statistics.mean(gap_times_ms) if gap_times_ms else 0,
                min_gap_ms=min(gap_times_ms) if gap_times_ms else 0,
                max_gap_ms=max(gap_times_ms) if gap_times_ms else 0,
                std_gap_ms=statistics.stdev(gap_times_ms) if len(gap_times_ms) > 1 else 0,
                avg_cpu_percent=statistics.mean(cpu_samples) if cpu_samples else 0,
                max_cpu_percent=max(cpu_samples) if cpu_samples else 0,
                avg_memory_mb=statistics.mean(memory_samples) if memory_samples else 0,
                max_memory_mb=max(memory_samples) if memory_samples else 0,
                crash_count=crash_count,
                restart_count=restart_count,
                errors=errors,
            )

            return result

        except Exception as e:
            logger.error(f"Option A benchmark failed: {e}", exc_info=True)
            raise
        finally:
            await manager.cleanup()

    async def run_option_b_benchmark(self) -> BenchmarkResult:
        """Benchmark Option B (spawn-per-track FFmpeg).

        Returns:
            BenchmarkResult for Option B
        """
        logger.info("=" * 60)
        logger.info("Running Option B Benchmark (Spawn-per-track)")
        logger.info("=" * 60)

        config = get_ffmpeg_config()
        manager = FFmpegProcessManager(config)

        gap_times_ms = []
        cpu_samples = []
        memory_samples = []
        errors = []
        crash_count = 0
        restart_count = 0

        try:
            # Start initial stream
            logger.info("Starting initial stream...")
            success = await manager.start_stream(self.test_loops[0])
            if not success:
                raise RuntimeError("Failed to start Option B stream")

            start_time = time.time()

            # Perform track switches
            for i in range(self.iterations):
                loop_idx = (i + 1) % len(self.test_loops)
                new_loop = self.test_loops[loop_idx]

                logger.info(f"Switch {i+1}/{self.iterations}: {new_loop}")

                # Measure gap time
                switch_start = time.time()
                success = await manager.switch_track(new_loop)
                switch_end = time.time()

                if success:
                    gap_ms = (switch_end - switch_start) * 1000
                    gap_times_ms.append(gap_ms)
                    logger.info(f"  Gap: {gap_ms:.2f}ms")
                else:
                    errors.append(f"Switch {i+1} failed")
                    crash_count += 1

                # Sample resource usage
                if manager._current_process and manager._current_process.process:
                    proc = manager._current_process.process
                    if proc.poll() is None:
                        try:
                            p = psutil.Process(proc.pid)
                            cpu_samples.append(p.cpu_percent(interval=0.1))
                            memory_samples.append(p.memory_info().rss / 1024 / 1024)
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass

                # Small delay between switches
                await asyncio.sleep(2)

            total_duration = time.time() - start_time

            # Stop stream
            await manager.stop_stream()

            # Calculate metrics
            result = BenchmarkResult(
                option_name="Option B (Spawn-per-track)",
                switch_count=len(gap_times_ms),
                total_duration_seconds=total_duration,
                avg_gap_ms=statistics.mean(gap_times_ms) if gap_times_ms else 0,
                min_gap_ms=min(gap_times_ms) if gap_times_ms else 0,
                max_gap_ms=max(gap_times_ms) if gap_times_ms else 0,
                std_gap_ms=statistics.stdev(gap_times_ms) if len(gap_times_ms) > 1 else 0,
                avg_cpu_percent=statistics.mean(cpu_samples) if cpu_samples else 0,
                max_cpu_percent=max(cpu_samples) if cpu_samples else 0,
                avg_memory_mb=statistics.mean(memory_samples) if memory_samples else 0,
                max_memory_mb=max(memory_samples) if memory_samples else 0,
                crash_count=crash_count,
                restart_count=restart_count,
                errors=errors,
            )

            return result

        except Exception as e:
            logger.error(f"Option B benchmark failed: {e}", exc_info=True)
            raise
        finally:
            await manager.cleanup()

    async def run_all_benchmarks(self) -> None:
        """Run all benchmarks and compare results."""
        logger.info("Starting benchmark comparison...")
        logger.info(f"Test loops: {len(self.test_loops)}")
        logger.info(f"Iterations: {self.iterations}")
        logger.info("")

        # Run Option B first (baseline)
        self.option_b_result = await self.run_option_b_benchmark()

        # Wait between benchmarks
        await asyncio.sleep(5)

        # Run Option A
        self.option_a_result = await self.run_option_a_benchmark()

        # Print comparison
        self.print_comparison()

    def print_comparison(self) -> None:
        """Print benchmark comparison results."""
        if not self.option_a_result or not self.option_b_result:
            logger.error("Cannot print comparison: missing results")
            return

        print("\n" + "=" * 80)
        print("BENCHMARK COMPARISON RESULTS")
        print("=" * 80)
        print("")

        # Gap comparison
        print("TRACK SWITCH GAP DURATION")
        print("-" * 80)
        print(f"{'Metric':<30} {'Option A':>20} {'Option B':>20}")
        print("-" * 80)
        print(
            f"{'Average Gap (ms)':<30} {self.option_a_result.avg_gap_ms:>20.2f} {self.option_b_result.avg_gap_ms:>20.2f}"
        )
        print(
            f"{'Min Gap (ms)':<30} {self.option_a_result.min_gap_ms:>20.2f} {self.option_b_result.min_gap_ms:>20.2f}"
        )
        print(
            f"{'Max Gap (ms)':<30} {self.option_a_result.max_gap_ms:>20.2f} {self.option_b_result.max_gap_ms:>20.2f}"
        )
        print(
            f"{'Std Dev (ms)':<30} {self.option_a_result.std_gap_ms:>20.2f} {self.option_b_result.std_gap_ms:>20.2f}"
        )
        print("")

        # Resource comparison
        print("RESOURCE USAGE")
        print("-" * 80)
        print(f"{'Metric':<30} {'Option A':>20} {'Option B':>20}")
        print("-" * 80)
        print(
            f"{'Average CPU (%)':<30} {self.option_a_result.avg_cpu_percent:>20.2f} {self.option_b_result.avg_cpu_percent:>20.2f}"
        )
        print(
            f"{'Max CPU (%)':<30} {self.option_a_result.max_cpu_percent:>20.2f} {self.option_b_result.max_cpu_percent:>20.2f}"
        )
        print(
            f"{'Average Memory (MB)':<30} {self.option_a_result.avg_memory_mb:>20.2f} {self.option_b_result.avg_memory_mb:>20.2f}"
        )
        print(
            f"{'Max Memory (MB)':<30} {self.option_a_result.max_memory_mb:>20.2f} {self.option_b_result.max_memory_mb:>20.2f}"
        )
        print("")

        # Stability comparison
        print("STABILITY")
        print("-" * 80)
        print(f"{'Metric':<30} {'Option A':>20} {'Option B':>20}")
        print("-" * 80)
        print(
            f"{'Successful Switches':<30} {self.option_a_result.switch_count:>20} {self.option_b_result.switch_count:>20}"
        )
        print(
            f"{'Crash Count':<30} {self.option_a_result.crash_count:>20} {self.option_b_result.crash_count:>20}"
        )
        print(
            f"{'Restart Count':<30} {self.option_a_result.restart_count:>20} {self.option_b_result.restart_count:>20}"
        )
        print("")

        # Summary
        print("SUMMARY")
        print("-" * 80)

        gap_improvement = (
            (self.option_b_result.avg_gap_ms - self.option_a_result.avg_gap_ms)
            / self.option_b_result.avg_gap_ms
        ) * 100
        cpu_diff = self.option_a_result.avg_cpu_percent - self.option_b_result.avg_cpu_percent
        mem_diff = self.option_a_result.avg_memory_mb - self.option_b_result.avg_memory_mb

        print(f"Gap Duration Improvement: {gap_improvement:+.1f}%")
        print(f"CPU Usage Difference: {cpu_diff:+.1f}%")
        print(f"Memory Usage Difference: {mem_diff:+.1f}MB")
        print("")

        if gap_improvement > 20:
            print("✅ Option A provides significantly better gap performance")
        elif gap_improvement > 0:
            print("✅ Option A provides marginally better gap performance")
        else:
            print("⚠️  Option A does not improve gap performance")

        print("=" * 80)


async def main():
    """Main entry point."""
    # Check for test loop files
    test_loops = []

    # Look for test loops in /srv/loops or current directory
    loop_dir = Path(os.getenv("LOOP_DIR", "/srv/loops"))
    if not loop_dir.exists():
        loop_dir = Path.cwd()

    # Find MP4 files
    for ext in ["*.mp4", "*.MP4"]:
        test_loops.extend(str(p) for p in loop_dir.glob(ext))

    if len(test_loops) < 2:
        logger.error("Need at least 2 test loop files to run benchmark")
        logger.error(f"Searched in: {loop_dir}")
        logger.error("Set LOOP_DIR environment variable to specify directory")
        sys.exit(1)

    # Limit to first 3 loops for testing
    test_loops = test_loops[:3]

    logger.info(f"Found {len(test_loops)} test loops")

    # Create and run benchmark
    runner = BenchmarkRunner(
        test_loops=test_loops,
        iterations=int(os.getenv("BENCHMARK_ITERATIONS", "10")),
        measure_duration=int(os.getenv("BENCHMARK_DURATION", "60")),
    )

    await runner.run_all_benchmarks()


if __name__ == "__main__":
    asyncio.run(main())
