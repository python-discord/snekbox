"""Calling functions with time limits."""
import multiprocessing
from collections.abc import Callable, Iterable, Mapping
from typing import Any, TypeVar

_T = TypeVar("_T")
_V = TypeVar("_V")

__all__ = ("timed",)


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
    with multiprocessing.Pool(1) as pool:
        result = pool.apply_async(func, args, kwds)
        try:
            return result.get(timeout)
        except multiprocessing.TimeoutError as e:
            raise TimeoutError(f"Call to {func.__name__} timed out after {timeout} seconds.") from e
