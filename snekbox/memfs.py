"""Memory filesystem for snekbox."""
from __future__ import annotations

import logging
from collections.abc import Generator
from functools import cached_property
from pathlib import Path
from types import TracebackType
from typing import Type
from uuid import uuid4

from snekbox.filesystem import mount, unmount
from snekbox.snekio import FileAttachment

log = logging.getLogger(__name__)

__all__ = ("MemFS", "parse_files")


def parse_files(
    fs: MemFS,
    files_limit: int,
    files_pattern: str,
    preload_dict: bool = False,
) -> list[FileAttachment]:
    """
    Parse files in a MemFS.

    Args:
        fs: The MemFS to parse.
        files_limit: The maximum number of files to parse.
        files_pattern: The glob pattern to match files against.
        preload_dict: Whether to preload as_dict property data.

    Returns:
        List of FileAttachments sorted lexically by path name.
    """
    res = sorted(fs.attachments(files_limit, files_pattern), key=lambda f: f.path)
    if preload_dict:
        for file in res:
            _ = file.as_dict
    return res


class MemFS:
    """A temporary directory using tmpfs."""

    def __init__(self, instance_size: int, root_dir: str | Path = "/memfs") -> None:
        """
        Create a temporary directory using tmpfs.

        Args:
            instance_size: Size limit of each tmpfs instance in bytes.
            root_dir: Root directory to mount instances in.
        """
        self.instance_size = instance_size
        self._path: Path | None = None
        self.root_dir: Path = Path(root_dir)
        self.root_dir.mkdir(exist_ok=True, parents=True)

    @cached_property
    def path(self) -> Path:
        """Returns the path of the MemFS."""
        if self._path is None:
            raise RuntimeError("MemFS accessed before __enter__.")
        return self._path

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
        """Mount a new tempfs and return self."""
        for _ in range(10):
            name = str(uuid4())
            try:
                path = self.root_dir / name
                path.mkdir()
                mount("", path, "tmpfs", size=self.instance_size)
                self._path = path
                break
            except FileExistsError:
                continue
        else:
            raise RuntimeError("Failed to generate a unique tempdir name in 10 attempts")

        self.mkdir(self.home)
        self.mkdir(self.output)
        return self

    def __exit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.cleanup()

    def mkdir(self, path: Path | str, chmod: int = 0o777) -> Path:
        """Create a directory in the tempdir."""
        folder = Path(self.path, path)
        folder.mkdir(parents=True, exist_ok=True)
        folder.chmod(chmod)
        return folder

    def attachments(
        self, max_count: int, pattern: str = "**/*"
    ) -> Generator[FileAttachment, None, None]:
        """
        Generate FileAttachments for files in the MemFS.

        Args:
            max_count: The maximum number of files to parse.
            pattern: The glob pattern to match files against.

        Yields:
            FileAttachments for files in the MemFS.
        """
        count = 0
        for file in self.output.rglob(pattern):
            if count > max_count:
                log.info(f"Max attachments {max_count} reached, skipping remaining files")
                break
            if file.is_file():
                count += 1
                yield FileAttachment.from_path(file, relative_to=self.output)

    def cleanup(self) -> None:
        """Unmount the tmpfs."""
        if self._path is None:
            return
        unmount(self.path)
        self.path.rmdir()
        self._path = None

    def __repr__(self):
        return f"<MemFS {self.name if self._path else '(Uninitialized)'}>"
