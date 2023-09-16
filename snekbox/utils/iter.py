from collections.abc import Generator, Iterable
from typing import TypeVar

__all__ = ("iter_lstrip",)

_T = TypeVar("_T")


def iter_lstrip(iterable: Iterable[_T]) -> Generator[_T, None, None]:
    """Remove leading falsy objects from an iterable."""
    it = iter(iterable)
    for item in it:
        if item:
            yield item
            break
    yield from it
