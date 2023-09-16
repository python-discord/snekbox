"""Calling functions with time limits."""
import signal
from collections.abc import Generator
from contextlib import contextmanager
from typing import TypeVar

_T = TypeVar("_T")
_V = TypeVar("_V")

__all__ = ("time_limit",)


@contextmanager
def time_limit(timeout: float) -> Generator[None, None, None]:
    """
    Decorator to call a function with a time limit.

    Args:
        timeout: Timeout limit in seconds.

    Raises:
        TimeoutError: If the function call takes longer than `timeout` seconds.
    """

    def signal_handler(_signum, _frame):
        raise TimeoutError(f"time_limit call timed out after {timeout} seconds.")

    # ITIMER_PROF would be more appropriate, but SIGPROF doesn't seem to interrupt sleeps.
    signal.signal(signal.SIGALRM, signal_handler)
    signal.setitimer(signal.ITIMER_REAL, timeout)

    try:
        yield
    finally:
        # Clear the timer if the function finishes early.
        signal.setitimer(signal.ITIMER_REAL, 0)
