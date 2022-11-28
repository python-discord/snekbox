"""I/O Operations for sending / receiving files from the sandbox."""
from __future__ import annotations

from base64 import b64decode, b64encode
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path


def safe_path(path: str) -> str:
    """
    Return `path` if there are no security issues.

    Raises:
        IllegalPathError: Raised on any path rule violation.
    """
    # Disallow absolute paths
    if Path(path).is_absolute():
        raise IllegalPathError(f"File path '{path}' must be relative")

    # Disallow traversal beyond root
    try:
        test_root = Path("/home")
        Path(test_root).joinpath(path).resolve().relative_to(test_root.resolve())
    except ValueError:
        raise IllegalPathError(f"File path '{path}' may not traverse beyond root")

    return path


class AttachmentError(ValueError):
    """Raised when an attachment is invalid."""


class ParsingError(AttachmentError):
    """Raised when an incoming file cannot be parsed."""


class IllegalPathError(ParsingError):
    """Raised when an attachment has an illegal path."""


@dataclass
class FileAttachment:
    """A file attachment."""

    path: str
    content: bytes

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> FileAttachment:
        """Convert a dict to an attachment."""
        path = safe_path(data["path"])
        content = b64decode(data.get("content", ""))
        return cls(path, content)

    @classmethod
    def from_path(cls, file: Path, relative_to: Path | None = None) -> FileAttachment:
        """
        Create an attachment from a file path.

        Args:
            file: The file to attach.
            relative_to: The root for the path name.
        """
        path = file.relative_to(relative_to) if relative_to else file
        return cls(str(path), file.read_bytes())

    @property
    def size(self) -> int:
        """Size of the attachment."""
        return len(self.content)

    def save_to(self, directory: Path | str) -> None:
        """Write the attachment to a file in `directory`."""
        file = Path(directory, self.path)
        # Create directories if they don't exist
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(self.content)

    @cached_property
    def json(self) -> dict[str, str]:
        """Convert the attachment to a dict."""
        content = b64encode(self.content).decode("ascii")
        return {
            "path": self.path,
            "size": self.size,
            "content": content,
        }
