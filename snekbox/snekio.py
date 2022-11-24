"""I/O Operations for sending / receiving files from the sandbox."""
from __future__ import annotations

from base64 import b64decode, b64encode
from dataclasses import dataclass
from pathlib import Path
from typing import Generic, TypeVar

T = TypeVar("T", str, bytes)


def safe_path(path: str) -> str:
    """
    Returns the `path` str if there are no security issues.

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
class FileAttachment(Generic[T]):
    """A file attachment."""

    path: str
    content: T

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> FileAttachment[bytes]:
        """Convert a dict to an attachment."""
        path = safe_path(data["path"])
        content = b64decode(data.get("content", ""))
        return cls(path, content)

    @classmethod
    def from_path(cls, file: Path, relative_to: Path | None = None) -> FileAttachment[bytes]:
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

    def as_bytes(self) -> bytes:
        """Return the attachment as bytes."""
        if isinstance(self.content, bytes):
            return self.content
        return self.content.encode("utf-8")

    def save_to(self, directory: Path | str) -> None:
        """Save the attachment to a path directory."""
        file = Path(directory, self.path)
        # Create directories if they don't exist
        file.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(self.content, str):
            file.write_text(self.content, encoding="utf-8")
        else:
            file.write_bytes(self.content)

    def to_dict(self) -> dict[str, str]:
        """Convert the attachment to a dict."""
        content = b64encode(self.as_bytes()).decode("ascii")
        return {
            "path": self.path,
            "size": self.size,
            "content": content,
        }
