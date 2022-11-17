"""Memory filesystem for snekbox."""
from __future__ import annotations

import logging
import subprocess
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from shutil import rmtree
from threading import BoundedSemaphore
from types import TracebackType
from typing import Type
from uuid import uuid4

from snekbox.snekio import FileAttachment

log = logging.getLogger(__name__)


NAMESPACE_DIR = Path("/memfs")
NAMESPACE_DIR.mkdir(exist_ok=True)
NAMESPACE_DIR.chmod(0o711)  # Execute only access for other users


def mount_tmpfs(name: str) -> Path:
    """Create and mount a tmpfs directory."""
    tmp = NAMESPACE_DIR / name
    tmp.mkdir()
    tmp.chmod(0o711)
    # Mount the tmpfs
    subprocess.check_call(
        [
            "mount",
            "-t",
            "tmpfs",
            "-o",
            f"size={MemFSOptions.MEMFS_SIZE_STR}",
            "tmpfs",
            str(tmp),
        ]
    )
    return tmp


def unmount_tmpfs(name: str) -> None:
    """Unmount and remove a tmpfs directory."""
    tmp = NAMESPACE_DIR / name
    subprocess.check_call(["umount", str(tmp)])
    rmtree(tmp, ignore_errors=True)


class MemFSOptions:
    """Options for memory file system."""

    # Size of the memory filesystem (per instance)
    MEMFS_SIZE = 48 * 1024 * 1024
    MEMFS_SIZE_STR = "48M"
    # Maximum number of files attachments will be scanned for
    MAX_FILES = 6
    # Maximum size of a file attachment (8 MiB)
    # 8 MB is also the discord bot upload limit
    MAX_FILE_SIZE = 8 * 1024 * 1024
    # Size of /dev/shm (16 MiB)
    SHM_SIZE = 16 * 1024 * 1024


class MemoryTempDir:
    """A temporary directory using tmpfs."""

    assignment_lock = BoundedSemaphore(1)
    assigned_names: set[str] = set()  # Pool of tempdir names in use

    def __init__(self) -> None:
        self.path: Path | None = None

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

    def __enter__(self) -> MemoryTempDir:
        # Generates a uuid tempdir
        with self.assignment_lock:
            for _ in range(10):
                name = str(uuid4())
                if name not in self.assigned_names:
                    self.path = mount_tmpfs(name)

                    # Create a home folder
                    home = self.path / "home"
                    home.mkdir()
                    home.chmod(0o777)

                    # Create a /dev/shm folder
                    shm = self.path / "dev" / "shm"
                    shm.mkdir(parents=True)
                    shm.chmod(0o777)

                    self.assigned_names.add(name)
                    return self
            else:
                raise RuntimeError("Failed to generate a unique tempdir name in 10 attempts")

    def __exit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.cleanup()

    @contextmanager
    def allow_write(self) -> None:
        """Temporarily allow writes to the root tempdir."""
        self.path.chmod(0o777)
        yield
        self.path.chmod(0o711)

    def attachments(self) -> Generator[FileAttachment, None, None]:
        """Return a list of attachments in the tempdir."""
        # Look for any file starting with `output`
        count = 0
        for file in self.home.glob("output*"):
            if count >= MemFSOptions.MAX_FILES:
                log.warning("Maximum number of attachments reached, skipping remaining files")
                break
            if file.is_file():
                count += 1
                yield FileAttachment.from_path(file, MemFSOptions.MAX_FILE_SIZE)

    def cleanup(self) -> None:
        """Remove files in temp dir, releases name."""
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
