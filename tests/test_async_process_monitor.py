"""Test the async process monitoring performance improvements."""

import asyncio
import os
import sys
import time
import pytest

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tron_ai.utils.process_monitor import ProcessMonitor


class TestAsyncProcessMonitor:
    """Test the async process monitoring improvements."""

    @pytest.mark.asyncio
    async def test_process_startup(self):
        """Test that processes start efficiently without blocking."""
        monitor = ProcessMonitor()

        # Start a simple process
        start_time = time.time()
        process_info = await monitor.start_process(
            server_name="test_server",
            command="python",
            args=["-c", "import time; print('Started'); time.sleep(1); print('Done')"],
        )
        startup_time = time.time() - start_time

        print(f"\n[Startup] Process started in {startup_time:.3f}s")
        assert startup_time < 0.5  # Should start quickly
        assert process_info.is_running
        assert process_info.pid is not None

        # Stop the process
        await monitor.stop_process("test_server")

    @pytest.mark.asyncio
    async def test_concurrent_process_monitoring(self):
        """Test monitoring multiple processes concurrently."""
        monitor = ProcessMonitor()

        # Start multiple processes
        start_time = time.time()
        tasks = []
        for i in range(5):
            task = monitor.start_process(
                server_name=f"server_{i}",
                command="python",
                args=["-c", f"import time; print('Server {i}'); time.sleep(0.5)"],
            )
            tasks.append(task)

        # Wait for all to start
        processes = await asyncio.gather(*tasks)
        startup_time = time.time() - start_time

        print(
            f"\n[Concurrent] Started {len(processes)} processes in {startup_time:.3f}s"
        )
        print(
            f"[Concurrent] Average startup time: {startup_time / len(processes):.3f}s per process"
        )

        # All should be running
        assert all(p.is_running for p in processes)
        assert startup_time < 1.0  # Should start all within 1 second

        # Check stats
        stats = monitor.get_all_stats()
        print(f"[Stats] {len(stats)} processes running")

        # Stop all processes
        await monitor.stop_all_processes()

    @pytest.mark.asyncio
    async def test_process_output_streaming(self):
        """Test that output is streamed efficiently without blocking."""
        monitor = ProcessMonitor()
        output_lines = []

        # Add output callback
        def output_callback(server_name, stream_type, line):
            output_lines.append((time.time(), server_name, stream_type, line))

        monitor.add_output_callback(output_callback)

        # Start process that produces output
        script = """
import time
import sys
for i in range(10):
    print(f"Line {i}", flush=True)
    time.sleep(0.1)
"""

        time.time()
        await monitor.start_process(
            server_name="output_test", command="python", args=["-c", script]
        )

        # Wait for process to complete
        await asyncio.sleep(1.5)

        print(f"\n[Output] Captured {len(output_lines)} lines")

        # Check that output was captured in real-time
        if len(output_lines) >= 2:
            first_time = output_lines[0][0]
            last_time = output_lines[-1][0]
            time_span = last_time - first_time
            print(f"[Output] Output spanning {time_span:.2f}s")
            assert time_span > 0.5  # Should span time, not all at once

        # Get buffered output
        buffered = monitor.get_process_output("output_test", "stdout", 5)
        print(f"[Output] Last 5 lines from buffer: {buffered}")

        await monitor.stop_all_processes()

    @pytest.mark.asyncio
    async def test_process_termination_handling(self):
        """Test graceful and forced termination."""
        monitor = ProcessMonitor()
        termination_events = []

        # Add termination callback
        def termination_callback(server_name, return_code):
            termination_events.append((server_name, return_code))

        monitor.add_termination_callback(termination_callback)

        # Start a process that exits normally
        await monitor.start_process(
            server_name="normal_exit",
            command="python",
            args=["-c", "print('Hello'); exit(0)"],
        )

        # Wait for normal termination
        await asyncio.sleep(0.5)

        assert len(termination_events) == 1
        assert termination_events[0] == ("normal_exit", 0)

        # Start a process that needs to be terminated
        await monitor.start_process(
            server_name="long_running",
            command="python",
            args=["-c", "import time; time.sleep(60)"],
        )

        # Stop it gracefully
        start_time = time.time()
        success = await monitor.stop_process("long_running", timeout=2.0)
        stop_time = time.time() - start_time

        print(f"\n[Termination] Process stopped in {stop_time:.3f}s")
        assert success
        assert stop_time < 3.0  # Should stop within timeout

    @pytest.mark.asyncio
    async def test_process_stats_monitoring(self):
        """Test process statistics collection."""
        monitor = ProcessMonitor()

        # Start a CPU-intensive process
        script = """
import time
# Busy loop to consume CPU
start = time.time()
while time.time() - start < 2:
    x = sum(range(1000))
"""

        process_info = await monitor.start_process(
            server_name="cpu_test", command="python", args=["-c", script]
        )

        # Let it run a bit
        await asyncio.sleep(0.5)

        # Get stats
        stats = monitor.get_process_stats("cpu_test")
        print(f"\n[Stats] Process stats: {stats}")

        assert stats is not None
        assert stats["is_running"] is True
        assert stats["pid"] == process_info.pid
        assert "uptime_seconds" in stats

        # These require psutil
        if "cpu_percent" in stats:
            print(f"[Stats] CPU usage: {stats['cpu_percent']:.1f}%")
            print(f"[Stats] Memory usage: {stats['memory_mb']:.1f}MB")

        await monitor.stop_all_processes()

    @pytest.mark.asyncio
    async def test_memory_efficiency(self):
        """Test that output buffering is memory-efficient."""
        monitor = ProcessMonitor(max_buffer_lines=100)

        # Start process that produces lots of output
        script = """
for i in range(1000):
    print(f"Line {i}: {'X' * 100}")
"""

        await monitor.start_process(
            server_name="memory_test", command="python", args=["-c", script]
        )

        # Wait for completion
        await asyncio.sleep(1.0)

        # Check buffer is limited
        output = monitor.get_process_output("memory_test", "stdout", 200)
        print(f"\n[Memory] Buffer contains {len(output)} lines (max 100)")
        assert len(output) <= 100  # Should be limited by max_buffer_lines

        await monitor.stop_all_processes()

    def test_sync_performance_comparison(self):
        """Compare async vs sync process monitoring performance."""
        print("\n" + "=" * 60)
        print("Async vs Sync Process Monitoring Comparison")
        print("=" * 60)

        # The real benefit of async is handling many processes with I/O
        # Let's test a more realistic scenario with output processing

        # Test: Monitor processes that produce output over time
        script = """
import time
import sys
for i in range(5):
    print(f"Output line {i}", flush=True)
    time.sleep(0.02)
"""

        num_processes = 3

        # Async version - truly concurrent monitoring
        async def async_test():
            monitor = ProcessMonitor()
            output_count = 0

            def count_output(server_name, stream_type, line):
                nonlocal output_count
                output_count += 1

            monitor.add_output_callback(count_output)

            start_time = time.time()

            # Start all processes concurrently
            tasks = []
            for i in range(num_processes):
                task = monitor.start_process(
                    server_name=f"async_{i}", command="python", args=["-c", script]
                )
                tasks.append(task)

            await asyncio.gather(*tasks)

            # Wait for all to complete
            await asyncio.sleep(0.2)
            await monitor.wait_for_all_monitors()

            elapsed = time.time() - start_time
            await monitor.stop_all_processes()

            return elapsed, output_count

        # Sync version - sequential with blocking I/O
        import subprocess
        import select

        start_time = time.time()
        sync_output_count = 0

        # Start and monitor each process (can't easily do concurrent)
        for i in range(num_processes):
            p = subprocess.Popen(
                ["python", "-c", script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )

            # Block monitoring this process before starting next
            while p.poll() is None:
                ready, _, _ = select.select([p.stdout], [], [], 0.01)
                for stream in ready:
                    line = stream.readline()
                    if line:
                        sync_output_count += 1

        sync_time = time.time() - start_time

        # Run async test
        async_time, async_output_count = asyncio.run(async_test())

        print(f"\nResults for {num_processes} processes producing output:")
        print(f"Sync: {sync_time:.3f}s, captured {sync_output_count} lines")
        print(f"Async: {async_time:.3f}s, captured {async_output_count} lines")

        # Async benefits:
        # 1. Starts all processes concurrently (not sequentially)
        # 2. Monitors all output streams simultaneously
        # 3. Non-blocking throughout

        # For this I/O bound scenario, async should be notably faster
        if num_processes > 1:
            # With multiple processes, async should show clear benefits
            print(f"Speedup: {sync_time / async_time:.1f}x")
            assert async_time < sync_time  # Async should be faster

        # Both should capture output successfully
        assert async_output_count > 0
        assert sync_output_count > 0


def benchmark_process_monitoring():
    """Run benchmarks for process monitoring."""
    print("\n" + "=" * 60)
    print("Process Monitoring Performance Benchmark")
    print("=" * 60)

    async def run_benchmark():
        monitor = ProcessMonitor()

        # Benchmark: Start many processes
        num_processes = 10
        start_time = time.time()

        tasks = []
        for i in range(num_processes):
            task = monitor.start_process(
                server_name=f"bench_{i}",
                command="python",
                args=["-c", f"print('Process {i}'); import time; time.sleep(1)"],
            )
            tasks.append(task)

        processes = await asyncio.gather(*tasks)
        startup_time = time.time() - start_time

        print(f"\nStarted {num_processes} processes in {startup_time:.3f}s")
        print(f"Average: {startup_time / num_processes * 1000:.1f}ms per process")

        # Check all are running
        running = sum(1 for p in processes if p.is_running)
        print(f"Running: {running}/{num_processes}")

        # Get all stats
        stats_time = time.time()
        all_stats = monitor.get_all_stats()
        stats_time = time.time() - stats_time
        print(
            f"Retrieved stats for {len(all_stats)} processes in {stats_time * 1000:.1f}ms"
        )

        # Stop all
        stop_time = time.time()
        await monitor.stop_all_processes()
        stop_time = time.time() - stop_time
        print(f"Stopped all processes in {stop_time:.3f}s")

    asyncio.run(run_benchmark())


if __name__ == "__main__":
    # Run the benchmark
    benchmark_process_monitoring()

    # Run the tests
    test = TestAsyncProcessMonitor()

    # Run sync test
    test.test_sync_performance_comparison()

    # Run async tests
    asyncio.run(test.test_process_startup())
    asyncio.run(test.test_concurrent_process_monitoring())
    asyncio.run(test.test_process_output_streaming())
    asyncio.run(test.test_process_termination_handling())
    asyncio.run(test.test_process_stats_monitoring())
    asyncio.run(test.test_memory_efficiency())

    print("\n✅ All async process monitoring tests passed!")
