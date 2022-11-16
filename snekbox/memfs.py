"""Memory filesystem for snekbox."""
from __future__ import annotations

import logging
import subprocess
from contextlib import contextmanager
from functools import cache
from pathlib import Path
from shutil import rmtree
from threading import BoundedSemaphore
from types import TracebackType
from typing import Type
from uuid import uuid4

MEMFS_SIZE = "2G"

log = logging.getLogger(__name__)


@cache
def mem_tempdir() -> Path:
    """Return the snekbox namespace temporary directory."""
    tmp = Path("/snekbox/memfs")
    if not tmp.exists() or not tmp.is_dir():
        # Create `memfs` and mount it as a tmpfs
        tmp.mkdir(parents=True, exist_ok=True)
        tmp.chmod(0o777)
        subprocess.check_call(
            ["mount", "-t", "tmpfs", "-o", f"size={MEMFS_SIZE}", "tmpfs", str(tmp)]
        )
        # Execute only access for other users
        tmp.chmod(0o711)

    return tmp


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

    def __enter__(self) -> MemoryTempDir:
        # Generates a uuid tempdir
        with self.assignment_lock:
            for _ in range(10):
                name = str(uuid4())
                if name not in self.assigned_names:
                    self.path = Path(mem_tempdir(), name)
                    self.path.mkdir()
                    self.path.chmod(0o555)
                    # Create a home folder
                    home = self.path / "home"
                    home.mkdir()
                    home.chmod(0o777)
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
        self.path.chmod(0o555)

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
