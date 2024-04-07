"""I/O Operations for sending / receiving files from the sandbox."""
from __future__ import annotations

from base64 import b64decode, b64encode
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from .errors import IllegalPathError, ParsingError

__all__ = ("safe_path", "FileAttachment")


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


@dataclass(frozen=True)
class FileAttachment:
    """A file attachment."""

    path: str
    content: bytes

    def __repr__(self) -> str:
        path = f"{self.path[:30]}..." if len(self.path) > 30 else self.path
        content = f"{self.content[:15]}..." if len(self.content) > 15 else self.content
        return f"{self.__class__.__name__}(path={path!r}, content={content!r})"

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> FileAttachment:
        """
        Convert a dict to an attachment.

        Raises:
            ParsingError: Raised when the dict has invalid base64 `content`.
        """
        path = safe_path(data["path"])
        try:
            content = b64decode(data.get("content", ""))
        except (TypeError, ValueError) as e:
            raise ParsingError(f"Invalid base64 encoding for file '{path}'") from e
        return cls(path, content)

    @classmethod
    def from_path(cls, file: Path, relative_to: Path | None = None) -> FileAttachment:
        """
        Create an attachment from a file path.

        Args:
            file: The file to attach.
            relative_to: The root for the path name.
        Raises:
            IllegalPathError: If path name contains characters that can't be encoded in UTF-8
        """
        path = file.relative_to(relative_to) if relative_to else file

        # Disallow filenames with chars that can't be encoded in UTF-8
        try:
            str(path).encode("utf-8")
        except UnicodeEncodeError as e:
            raise IllegalPathError("File paths may not contain invalid byte sequences") from e

        return cls(str(path), file.read_bytes())

    @property
    def size(self) -> int:
        """Size of the attachment."""
        return len(self.content)

    def save_to(self, directory: Path | str) -> Path:
        """Write the attachment to a file in `directory`. Return a Path of the file."""
        file = Path(directory, self.path)
        # Create directories if they don't exist
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(self.content)
        return file

    @cached_property
    def as_dict(self) -> dict[str, str | int]:
        """Convert the attachment to a dict."""
        content = b64encode(self.content).decode("ascii")
        return {
            "path": self.path,
            "size": self.size,
            "content": content,
        }
