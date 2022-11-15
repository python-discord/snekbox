"""Memory filesystem for snekbox."""

import logging
from functools import cache
from pathlib import Path
from shutil import rmtree
from threading import BoundedSemaphore
from uuid import uuid4, uuid5

from typing_extensions import Self

NAMESPACE = "com.snekbox"

log = logging.getLogger(__name__)


@cache
def shm_tempdir() -> Path:
    """Return the snekbox namespace temporary directory."""
    shm = Path("/dev/shm")
    if not shm.exists() or not shm.is_dir():
        raise RuntimeError("No /dev/shm found")

    # Create a temporary directory in the snekbox namespace
    tempdir = Path(shm, NAMESPACE)
    tempdir.mkdir(exist_ok=True)
    return tempdir


class MemoryTempDir:
    """A temporary directory using tmpfs."""
    assignment_lock = BoundedSemaphore(1)  # Only one process can assign a tempdir at a time
    assigned_names: set[str] = set()  # Pool of tempdir names in use

    def __init__(self) -> None:
        self.path: Path | None = None
        pass

    @property
    def name(self) -> str | None:
        """Name of the temp dir."""
        if self.path is None:
            return None
        return self.path.name

    def __enter__(self) -> Self:
        # Generates a uuid tempdir
        with self.assignment_lock:
            for _ in range(10):
                name = str(uuid4())
                if name not in self.assigned_names:
                    self.path = Path(shm_tempdir(), name)
                    self.path.mkdir()
                    self.assigned_names.add(name)
                    return self
            else:
                raise RuntimeError("Failed to generate a unique tempdir name in 10 attempts")

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

    def cleanup(self) -> None:
        """Remove files in temp dir, releases name."""
        if self.path is None:
            return
        # Remove the path folder
        rmtree(self.path, ignore_errors=True)

        if not self.path.exists():
            with self.assignment_lock:
                self.assigned_names.remove(self.name)
        else:
            # Don't remove name from pool if failed to delete folder
            logging.warning(f"Failed to remove {self.path} in cleanup")

        self.path = None

    def __repr__(self):
        return f"<MemoryTempDir {self.name or '(Uninitialized)'}>"
