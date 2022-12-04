"""Memory filesystem for snekbox."""
from __future__ import annotations

import logging
import warnings
import weakref
from collections.abc import Generator
from contextlib import suppress
from pathlib import Path
from types import TracebackType
from typing import Type
from uuid import uuid4

from snekbox.filesystem import mount, unmount
from snekbox.snekio import FileAttachment

log = logging.getLogger(__name__)

__all__ = ("MemFS",)


class MemFS:
    """An in-memory temporary file system."""

    def __init__(self, instance_size: int, root_dir: str | Path = "/memfs") -> None:
        """
        Initialize an in-memory temporary file system.

        Examples:
            >>> with MemFS(1024) as memfs:
            ...     (memfs.home / "test.txt").write_text("Hello")

        Args:
            instance_size: Size limit of each tmpfs instance in bytes.
            root_dir: Root directory to mount instances in.
        """
        self.instance_size = instance_size
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(exist_ok=True, parents=True)

        for _ in range(10):
            name = str(uuid4())
            try:
                self.path = self.root_dir / name
                self.path.mkdir()
                mount("", self.path, "tmpfs", size=self.instance_size)
                break
            except OSError:
                continue
        else:
            raise RuntimeError("Failed to generate a unique MemFS name in 10 attempts")

        self.mkdir(self.home)
        self.mkdir(self.output)

        self._finalizer = weakref.finalize(
            self,
            self._cleanup,
            self.path,
            warn_message=f"Implicitly cleaning up {self!r}",
        )

    @classmethod
    def _cleanup(cls, path: Path, warn_message: str):
        """Implicit cleanup of the MemFS."""
        with suppress(OSError):
            unmount(path)
            path.rmdir()
        warnings.warn(warn_message, ResourceWarning)

    def cleanup(self) -> None:
        """Unmount the tempfs and remove the directory."""
        if self._finalizer.detach() or self.path.exists():
            unmount(self.path)
            self.path.rmdir()

    @property
    def name(self) -> str:
        """Name of the temp dir."""
        return self.path.name

    @property
    def home(self) -> Path:
        """Path to home directory."""
        return self.path / "home"

    @property
    def output(self) -> Path:
        """Path to output directory."""
        return self.home / "output"

    def __enter__(self) -> MemFS:
        return self

    def __exit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.cleanup()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.path}>"

    def mkdir(self, path: Path | str, chmod: int = 0o777) -> Path:
        """Create a directory in the tempdir."""
        folder = Path(self.path, path)
        folder.mkdir(parents=True, exist_ok=True)
        folder.chmod(chmod)
        return folder

    def files(self, limit: int, pattern: str = "**/*") -> Generator[FileAttachment, None, None]:
        """
        Yields FileAttachments for files in the MemFS.

        Args:
            limit: The maximum number of files to parse.
            pattern: The glob pattern to match files against.
        """
        count = 0
        for file in self.output.rglob(pattern):
            if count > limit:
                log.info(f"Max attachments {limit} reached, skipping remaining files")
                break
            if file.is_file():
                count += 1
                yield FileAttachment.from_path(file, relative_to=self.output)

    def files_list(
        self,
        limit: int,
        pattern: str,
        preload_dict: bool = False,
    ) -> list[FileAttachment]:
        """
        Return a sorted list of output files found in the MemFS.

        Args:
            limit: The maximum number of files to parse.
            pattern: The glob pattern to match files against.
            preload_dict: Whether to preload as_dict property data.

        Returns:
            List of FileAttachments sorted lexically by path name.
        """
        res = sorted(self.files(limit, pattern), key=lambda f: f.path)
        if preload_dict:
            for file in res:
                # Loads the cached property as attribute
                _ = file.as_dict
        return res
