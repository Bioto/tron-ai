"""
Centralized JSON utilities using orjson for performance.

This module provides a unified interface for JSON operations using orjson
for significantly better performance (2-10x faster than standard json).
Falls back to standard json if orjson is not available.
"""

import logging
from typing import Any, Union

try:
    import orjson

    HAS_ORJSON = True
except ImportError:
    import json as _json

    HAS_ORJSON = False
    logging.warning(
        "orjson not available, falling back to standard json (slower performance)"
    )


def dumps(obj: Any, **kwargs) -> Union[str, bytes]:
    """
    Serialize object to JSON string.

    Args:
        obj: Object to serialize
        **kwargs: Additional arguments (ignored for orjson compatibility)

    Returns:
        JSON string (str if standard json, bytes if orjson)
    """
    if HAS_ORJSON:
        # orjson returns bytes, decode to str for compatibility
        options = 0
        if kwargs.get("sort_keys"):
            options |= orjson.OPT_SORT_KEYS
        if kwargs.get("indent"):
            options |= orjson.OPT_INDENT_2

        result = orjson.dumps(obj, option=options)
        # Return as string for compatibility
        return result.decode("utf-8")
    else:
        return _json.dumps(obj, **kwargs)


def loads(s: Union[str, bytes]) -> Any:
    """
    Deserialize JSON string to object.

    Args:
        s: JSON string or bytes to deserialize

    Returns:
        Deserialized object
    """
    if HAS_ORJSON:
        return orjson.loads(s)
    else:
        if isinstance(s, bytes):
            s = s.decode("utf-8")
        return _json.loads(s)


def load(fp) -> Any:
    """
    Load JSON from file-like object.

    Args:
        fp: File-like object to read from

    Returns:
        Deserialized object
    """
    content = fp.read()
    return loads(content)


def dump(obj: Any, fp, **kwargs) -> None:
    """
    Dump object to file-like object as JSON.

    Args:
        obj: Object to serialize
        fp: File-like object to write to
        **kwargs: Additional arguments
    """
    json_str = dumps(obj, **kwargs)
    if isinstance(json_str, bytes):
        json_str = json_str.decode("utf-8")
    fp.write(json_str)


def pretty_dumps(obj: Any) -> str:
    """
    Serialize object to pretty-printed JSON string.

    Args:
        obj: Object to serialize

    Returns:
        Pretty-printed JSON string
    """
    return dumps(obj, indent=2, sort_keys=True)


# Performance comparison utilities
def benchmark_json_performance(data: Any, iterations: int = 1000) -> dict:
    """
    Benchmark JSON serialization performance.

    Args:
        data: Data to benchmark
        iterations: Number of iterations

    Returns:
        Dictionary with performance metrics
    """
    import time

    # Test serialization
    start = time.time()
    for _ in range(iterations):
        dumps(data)
    orjson_or_std_time = time.time() - start

    if HAS_ORJSON:
        # Compare with standard json if using orjson
        import json as _std_json

        start = time.time()
        for _ in range(iterations):
            _std_json.dumps(data)
        std_time = time.time() - start

        return {
            "orjson_time": orjson_or_std_time,
            "standard_json_time": std_time,
            "speedup": std_time / orjson_or_std_time,
            "using_orjson": True,
        }
    else:
        return {
            "time": orjson_or_std_time,
            "using_orjson": False,
        }


# Export the main functions
__all__ = ["dumps", "loads", "load", "dump", "pretty_dumps", "HAS_ORJSON"]
