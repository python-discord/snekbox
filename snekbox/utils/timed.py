"""Calling functions with time limits."""
from collections.abc import Callable, Iterable, Mapping
from multiprocessing import Pool
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

    Raises:
        TimeoutError: If the function call takes longer than `timeout` seconds.
    """
    if kwds is None:
        kwds = {}
    with Pool(1) as pool:
        result = pool.apply_async(func, args, kwds)
        return result.get(timeout)
