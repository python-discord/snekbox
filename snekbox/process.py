"""Utilities for process management."""
from collections.abc import Sequence
from os import PathLike
from subprocess import CompletedProcess
from typing import TypeVar

from snekbox.snekio import FileAttachment

_T = TypeVar("_T")
ArgType = (
    str
    | bytes
    | PathLike[str]
    | PathLike[bytes]
    | Sequence[str | bytes | PathLike[str] | PathLike[bytes]]
)


class EvalResult(CompletedProcess[_T]):
    """An evaluation job that has finished running."""

    def __init__(
        self,
        args: ArgType,
        returncode: int | None,
        stdout: _T | None = None,
        stderr: _T | None = None,
        attachments: list[FileAttachment] | None = None,
    ) -> None:
        """Create an evaluation result."""
        super().__init__(args, returncode, stdout, stderr)
        self.attachments: list[FileAttachment] = attachments or []
