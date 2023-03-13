"""Calling functions with time limits."""
import multiprocessing
import signal
from collections.abc import Callable, Generator, Iterable, Mapping
from contextlib import contextmanager
from typing import Any, TypeVar

_T = TypeVar("_T")
_V = TypeVar("_V")

__all__ = ("timed", "time_limit")


def timed(
    func: Callable[[_T], _V],
    args: Iterable = (),
    kwds: Mapping[str, Any] | None = None,
    timeout: float | None = None,
) -> _V:
    """
    Call a function with a time limit.

    Args:
        func: Function to call.
        args: Arguments for function.
        kwds: Keyword arguments for function.
        timeout: Timeout limit in seconds.

    Raises:
        TimeoutError: If the function call takes longer than `timeout` seconds.
    """
    if kwds is None:
        kwds = {}
    with multiprocessing.Pool(1, maxtasksperchild=1) as pool:
        result = pool.apply_async(func, args, kwds)
        try:
            return result.get(timeout)
        except multiprocessing.TimeoutError as e:
            raise TimeoutError(f"Call to {func.__name__} timed out after {timeout} seconds.") from e


@contextmanager
def time_limit(timeout: int | None = None) -> Generator[None, None, None]:
    """
    Decorator to call a function with a time limit. Uses SIGALRM, requires a UNIX system.

    Args:
        timeout: Timeout limit in seconds.

    Raises:
        TimeoutError: If the function call takes longer than `timeout` seconds.
    """

    def signal_handler(signum, frame):
        raise TimeoutError(f"time_limit call timed out after {timeout} seconds.")

    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(timeout)

    try:
        yield
    finally:
        signal.alarm(0)
