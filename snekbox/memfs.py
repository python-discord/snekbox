"""Memory filesystem for snekbox."""
from __future__ import annotations

import logging
import os
import subprocess
from collections.abc import Generator
from pathlib import Path
from threading import BoundedSemaphore
from types import TracebackType
from typing import Type
from uuid import uuid4

from snekbox.snekio import FileAttachment

log = logging.getLogger(__name__)

PID = os.getpid()

NAMESPACE_DIR = Path("/memfs")
NAMESPACE_DIR.mkdir(exist_ok=True)


def mount_tmpfs(name: str, size: int | str) -> Path:
    """Create and mount a tmpfs directory."""
    tmp = NAMESPACE_DIR / name
    tmp.mkdir()
    # Mount the tmpfs
    subprocess.check_call(
        [
            "mount",
            "-t",
            "tmpfs",
            "-o",
            f"size={size}",
            "tmpfs",
            str(tmp),
        ]
    )
    return tmp


def unmount_tmpfs(name: str) -> None:
    """Unmount and remove a tmpfs directory."""
    tmp = NAMESPACE_DIR / name
    subprocess.check_call(["umount", str(tmp)])
    # Unmounting will not remove the original folder, so do that here
    tmp.rmdir()


class MemFS:
    """A temporary directory using tmpfs."""

    assignment_lock = BoundedSemaphore(1)
    assigned_names: set[str] = set()  # Pool of tempdir names in use

    def __init__(self, instance_size: int) -> None:
        """
        Create a temporary directory using tmpfs.

        size: Size limit of each tmpfs instance in bytes
        """
        self.path: Path | None = None
        self.instance_size = instance_size

    @property
    def name(self) -> str | None:
        """Name of the temp dir."""
        return self.path.name if self.path else None

    @property
    def home(self) -> Path | None:
        """Path to home directory."""
        return Path(self.path, "home") if self.path else None

    @property
    def shm(self) -> Path | None:
        """Path to /dev/shm."""
        return Path(self.path, "dev", "shm") if self.path else None

    def __enter__(self) -> MemFS:
        # Generates a uuid tempdir
        with self.assignment_lock:
            for _ in range(10):
                # Combine PID to avoid collisions with multiple snekbox processes
                if (name := f"{PID}-{uuid4()}") not in self.assigned_names:
                    self.path = mount_tmpfs(name, self.instance_size)
                    self.assigned_names.add(name)
                    break
            else:
                raise RuntimeError("Failed to generate a unique tempdir name in 10 attempts")

        self.mkdir("home")
        self.mkdir("dev/shm")
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
        self, max_count: int, max_size: int | None = None
    ) -> Generator[FileAttachment, None, None]:
        """Return a list of attachments in the tempdir."""
        count = 0
        # Look for any file starting with `output`
        for file in self.home.glob("output*"):
            if count > max_count:
                log.info(f"Max attachments {max_count} reached, skipping remaining files")
                break
            if file.is_file():
                count += 1
                yield FileAttachment.from_path(file, max_size)

    def cleanup(self) -> None:
        """Unmounts tmpfs, releases name."""
        if self.path is None:
            return
        # Remove the path folder
        unmount_tmpfs(self.name)

        if not self.path.exists():
            with self.assignment_lock:
                self.assigned_names.remove(self.name)
        else:
            # Don't remove name from pool if failed to delete folder
            logging.warning(f"Failed to remove {self.path} in cleanup")

        self.path = None

    def __repr__(self):
        return f"<MemoryTempDir {self.name or '(Uninitialized)'}>"
