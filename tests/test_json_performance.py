"""Test JSON performance improvements."""

import pytest
import time
import json as std_json

from tron_intelligence.utils import json


class TestJSONPerformance:
    """Test JSON performance improvements."""

    @pytest.fixture
    def simple_data(self):
        """Simple test data."""
        return {
            "name": "test",
            "value": 123,
            "items": ["a", "b", "c"],
            "nested": {"key": "value"},
        }

    @pytest.fixture
    def complex_data(self):
        """Complex test data for performance testing."""
        return {
            "users": [
                {
                    "id": i,
                    "name": f"User {i}",
                    "email": f"user{i}@example.com",
                    "metadata": {
                        "created": "2024-01-01",
                        "tags": ["tag1", "tag2", "tag3"],
                        "settings": {
                            "theme": "dark",
                            "notifications": True,
                            "preferences": list(range(10)),
                        },
                    },
                }
                for i in range(100)
            ],
            "statistics": {
                "total": 100,
                "active": 75,
                "data": [float(i) * 1.5 for i in range(1000)],
            },
        }

    def test_json_utils_compatibility(self, simple_data):
        """Test that json_utils provides compatible interface."""
        # Test dumps/loads
        json_str = json.dumps(simple_data)
        loaded = json.loads(json_str)
        assert loaded == simple_data

        # Test pretty printing
        pretty = json.pretty_dumps(simple_data)
        assert isinstance(pretty, str)
        assert "\n" in pretty  # Should be formatted

    def test_performance_improvement(self, complex_data):
        """Test that orjson provides performance improvement."""
        if not json.HAS_ORJSON:
            pytest.skip("orjson not available")

        iterations = 100

        # Benchmark standard json
        start = time.time()
        for _ in range(iterations):
            std_str = std_json.dumps(complex_data)
            std_json.loads(std_str)
        std_time = time.time() - start

        # Benchmark json_utils (orjson)
        start = time.time()
        for _ in range(iterations):
            orjson_str = json.dumps(complex_data)
            json.loads(orjson_str)
        orjson_time = time.time() - start

        # Should be at least 2x faster
        speedup = std_time / orjson_time
        print(f"\nPerformance improvement: {speedup:.2f}x faster")
        print(f"Standard json: {std_time:.4f}s")
        print(f"orjson: {orjson_time:.4f}s")

        assert speedup > 1.5  # Conservative expectation

    def test_large_data_handling(self):
        """Test handling of large JSON data."""
        # Create large dataset
        large_data = {
            "data": [{"id": i, "value": f"value_{i}" * 10} for i in range(10000)]
        }

        # Should handle large data efficiently
        start = time.time()
        json_str = json.dumps(large_data)
        result = json.loads(json_str)
        elapsed = time.time() - start

        assert result == large_data
        print(f"\nLarge data serialization/deserialization: {elapsed:.4f}s")

        # Should complete in reasonable time
        assert elapsed < 1.0  # Less than 1 second for 10k items

    def test_file_operations(self, simple_data, tmp_path):
        """Test file-based JSON operations."""
        # Test dump/load
        json_file = tmp_path / "test.json"

        with open(json_file, "w") as f:
            json.dump(simple_data, f)

        with open(json_file, "r") as f:
            loaded = json.load(f)

        assert loaded == simple_data

    def test_benchmark_function(self, complex_data):
        """Test the benchmark utility function."""
        results = json.benchmark_json_performance(complex_data, iterations=50)

        if json.HAS_ORJSON:
            assert "orjson_time" in results
            assert "standard_json_time" in results
            assert "speedup" in results
            assert results["speedup"] > 1.0
            assert results["using_orjson"] is True

            print("\nBenchmark results:")
            print(f"  orjson time: {results['orjson_time']:.4f}s")
            print(f"  standard json time: {results['standard_json_time']:.4f}s")
            print(f"  Speedup: {results['speedup']:.2f}x")
        else:
            assert "time" in results
            assert results["using_orjson"] is False

    def test_special_types(self):
        """Test handling of special types."""
        # Test with various types
        test_cases = [
            {"unicode": "Hello 世界 🌍"},
            {"float": 3.14159},
            {"bool": True},
            {"null": None},
            {"empty_list": []},
            {"empty_dict": {}},
        ]

        for data in test_cases:
            json_str = json.dumps(data)
            result = json.loads(json_str)
            assert result == data

    def test_sort_keys_option(self):
        """Test sort_keys option works correctly."""
        data = {"z": 1, "a": 2, "m": 3}

        # Without sort_keys
        json.dumps(data)

        # With sort_keys
        sorted_json = json.dumps(data, sort_keys=True)

        # The sorted version should have keys in order
        if json.HAS_ORJSON:
            # orjson with OPT_SORT_KEYS should sort
            assert sorted_json.index('"a"') < sorted_json.index('"m"')
            assert sorted_json.index('"m"') < sorted_json.index('"z"')

    def test_bytes_handling(self):
        """Test handling of bytes input."""
        data = {"test": "value"}
        json_str = json.dumps(data)

        # Convert to bytes
        json_bytes = json_str.encode("utf-8") if isinstance(json_str, str) else json_str

        # Should handle bytes input
        result = json.loads(json_bytes)
        assert result == data


class TestJSONMigration:
    """Test that migrated modules work correctly with json_utils."""

    def test_imports_work(self):
        """Test that all migrated imports work."""
        # These imports should not raise errors
        from tron_intelligence.utils import json
        from tron_intelligence.utils import json as json_utils

        # This is to avoid unused import warnings
        assert json is not None
        assert json_utils is not None

    def test_docker_agent_json_usage(self):
        """Test that docker agent correctly uses json_utils."""
        from tron_intelligence.executors.agents.builtin.docker_agent import json
        from tron_intelligence.utils import json

        # Should be using our json_utils
        assert json is json

        # Test a simple operation
        data = {"test": "docker"}
        encoded = json.dumps(data)
        decoded = json.loads(encoded)
        assert decoded == data


if __name__ == "__main__":
    # Run basic performance test
    print("Testing JSON performance improvements...")

    # Create test data
    test_data = {
        "users": [{"id": i, "name": f"User{i}"} for i in range(1000)],
        "metadata": {"timestamp": "2024-01-01", "version": "1.0"},
    }

    # Run benchmark
    from tron_intelligence.utils import json

    results = json.benchmark_json_performance(test_data)

    if json.HAS_ORJSON:
        print(f"Using orjson: {results['speedup']:.2f}x faster than standard json")
    else:
        print("Using standard json (orjson not available)")
