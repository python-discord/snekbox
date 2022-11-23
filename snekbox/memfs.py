"""Memory filesystem for snekbox."""
from __future__ import annotations

import logging
import subprocess
from collections.abc import Generator
from functools import cached_property
from pathlib import Path
from types import TracebackType
from typing import Type
from uuid import uuid4

from snekbox.snekio import FileAttachment

log = logging.getLogger(__name__)


def mount_tmpfs(path: str | Path, size: int | str) -> Path:
    """Create and mount a tmpfs directory."""
    path = Path(path)
    path.mkdir()
    # Mount the tmpfs
    subprocess.check_call(
        [
            "mount",
            "-t",
            "tmpfs",
            "-o",
            f"size={size}",
            "tmpfs",
            str(path),
        ]
    )
    return path


def unmount_tmpfs(path: str | Path) -> None:
    """Unmount and remove a tmpfs directory."""
    path = Path(path)
    subprocess.check_call(["umount", str(path)])
    # Unmounting will not remove the original folder, so do that here
    path.rmdir()


def parse_files(
    fs: MemFS,
    files_limit: int,
    files_pattern: str,
) -> list[FileAttachment]:
    """
    Parse files in a MemFS.

    Returns:
        List of FileAttachments sorted lexically by path name.
    """
    return sorted(fs.attachments(files_limit, files_pattern), key=lambda file: file.path)


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
    def name(self) -> str | None:
        """Name of the temp dir."""
        return self.path.name

    @property
    def home(self) -> Path | None:
        """Path to home directory."""
        return Path(self.path, "home")

    def __enter__(self) -> MemFS:
        """Mounts a new tempfs, returns self."""
        for _ in range(10):
            name = str(uuid4())
            try:
                path = self.root_dir / name
                self._path = mount_tmpfs(path, self.instance_size)
                break
            except FileExistsError:
                continue
        else:
            raise RuntimeError("Failed to generate a unique tempdir name in 10 attempts")

        self.mkdir("home")
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
        self, max_count: int, pattern: str = "output*"
    ) -> Generator[FileAttachment, None, None]:
        """Return a list of attachments in the tempdir."""
        count = 0
        for file in self.home.glob(pattern):
            if count > max_count:
                log.info(f"Max attachments {max_count} reached, skipping remaining files")
                break
            if file.is_file():
                count += 1
                yield FileAttachment.from_path(file)

    def cleanup(self) -> None:
        """Unmounts tmpfs."""
        if self._path is None:
            return
        unmount_tmpfs(self.path)
        self._path = None

    def __repr__(self):
        return f"<MemFS {self.name if self._path else '(Uninitialized)'}>"
