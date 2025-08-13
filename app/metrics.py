"""Metrics and timing utilities."""
import time
from contextlib import contextmanager
from loguru import logger


@contextmanager
def time_block(operation_name: str):
    """Context manager for timing operations."""
    start_time = time.time()
    try:
        yield
    finally:
        elapsed_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        logger.debug(f"TIMER {operation_name}: {elapsed_time:.2f} ms")
