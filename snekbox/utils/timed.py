"""Calling functions with time limits."""
import signal
from collections.abc import Generator
from contextlib import contextmanager
from typing import TypeVar

_T = TypeVar("_T")
_V = TypeVar("_V")

__all__ = ("time_limit",)


@contextmanager
def time_limit(timeout: int | None = None) -> Generator[None, None, None]:
    """
    Decorator to call a function with a time limit.

    Args:
        timeout: Timeout limit in seconds.

    Raises:
        TimeoutError: If the function call takes longer than `timeout` seconds.
    """

    def signal_handler(_signum, _frame):
        raise TimeoutError(f"time_limit call timed out after {timeout} seconds.")

    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(timeout)

    try:
        yield
    finally:
        signal.alarm(0)
