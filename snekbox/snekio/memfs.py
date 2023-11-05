"""Memory filesystem for snekbox."""
from __future__ import annotations

import glob
import logging
import time
import warnings
import weakref
from collections.abc import Generator
from contextlib import suppress
from pathlib import Path
from types import TracebackType
from typing import Type
from uuid import uuid4

from snekbox.snekio import FileAttachment
from snekbox.snekio.filesystem import mount, unmount

log = logging.getLogger(__name__)

__all__ = ("MemFS",)


class MemFS:
    """An in-memory temporary file system."""

    def __init__(
        self,
        instance_size: int,
        root_dir: str | Path = "/memfs",
        home: str = "home",
        output: str = "home",
    ) -> None:
        """
        Initialize an in-memory temporary file system.

        Examples:
            >>> with MemFS(1024) as memfs:
            ...     (memfs.home / "test.txt").write_text("Hello")

        Args:
            instance_size: Size limit of each tmpfs instance in bytes.
            root_dir: Root directory to mount instances in.
            home: Name of the home directory.
            output: Name of the output directory within home. If empty, uses home.
        """
        self.instance_size = instance_size
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(exist_ok=True, parents=True)
        self._home_name = home
        self._output_name = output

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
        return self.path / self._home_name

    @property
    def output(self) -> Path:
        """Path to output directory."""
        return self.path / self._output_name

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

    def files(
        self,
        limit: int,
        pattern: str = "**/*",
        exclude_files: dict[Path, float] | None = None,
        timeout: float | None = None,
    ) -> Generator[FileAttachment, None, None]:
        """
        Yields FileAttachments for files found in the output directory.

        Args:
            limit: The maximum number of files to parse.
            pattern: The glob pattern to match files against.
            exclude_files: A dict of Paths and last modified times.
                Files will be excluded if their last modified time
                is equal to the provided value.
            timeout: Maximum time in seconds for file parsing.
        Raises:
            TimeoutError: If file parsing exceeds timeout.
        """
        start_time = time.monotonic()
        count = 0
        total_size = 0
        files = glob.iglob(pattern, root_dir=str(self.output), recursive=True, include_hidden=False)
        for file in (Path(self.output, f) for f in files):
            if timeout and (time.monotonic() - start_time) > timeout:
                raise TimeoutError("File parsing timeout exceeded in MemFS.files")

            if not file.is_file():
                continue

            # file.is_file allows file to be a regular file OR a symlink pointing to a regular file.
            # It is important that we follow symlinks here, so when we check st_size later it is the
            # size of the underlying file rather than of the symlink.
            stat = file.stat(follow_symlinks=True)

            if exclude_files and (orig_time := exclude_files.get(file)):
                new_time = stat.st_mtime
                log.info(f"Checking {file.name} ({orig_time=}, {new_time=})")
                if stat.st_mtime == orig_time:
                    log.info(f"Skipping {file.name!r} as it has not been modified")
                    continue

            if count > limit:
                log.info(f"Max attachments {limit} reached, skipping remaining files")
                break

            # Due to sparse files and links the total size could end up being greater
            # than the size limit of the tmpfs. Limit the total size to be read to
            # prevent high memory usage / OOM when reading files.
            total_size += stat.st_size
            if total_size > self.instance_size:
                log.info(f"Max file size {self.instance_size} reached, skipping remaining files")
                break

            count += 1
            log.info(f"Found valid file for upload {file.name!r}")
            yield FileAttachment.from_path(file, relative_to=self.output)

    def files_list(
        self,
        limit: int,
        pattern: str,
        exclude_files: dict[Path, float] | None = None,
        preload_dict: bool = False,
        timeout: float | None = None,
    ) -> list[FileAttachment]:
        """
        Return a sorted list of file paths within the output directory.

        Args:
            limit: The maximum number of files to parse.
            pattern: The glob pattern to match files against.
            exclude_files: A dict of Paths and last modified times.
                Files will be excluded if their last modified time
                is equal to the provided value.
            preload_dict: Whether to preload as_dict property data.
            timeout: Maximum time in seconds for file parsing.
        Returns:
            List of FileAttachments sorted lexically by path name.
        Raises:
            TimeoutError: If file parsing exceeds timeout.
        """
        start_time = time.monotonic()
        res = sorted(
            self.files(limit=limit, pattern=pattern, exclude_files=exclude_files),
            key=lambda f: f.path,
        )
        if preload_dict:
            for file in res:
                if timeout and (time.monotonic() - start_time) > timeout:
                    raise TimeoutError("File parsing timeout exceeded in MemFS.files_list")
                # Loads the cached property as attribute
                _ = file.as_dict
        return res
