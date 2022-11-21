"""I/O Operations for sending / receiving files from the sandbox."""
from __future__ import annotations

import zlib
from base64 import b64decode, b64encode
from dataclasses import dataclass
from pathlib import Path
from typing import Generic, TypeVar

RequestType = dict[str, str | bool | list[str | dict[str, str]]]

T = TypeVar("T", str, bytes)


def sizeof_fmt(num: int, suffix: str = "B") -> str:
    """Return a human-readable file size."""
    for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"):
        if abs(num) < 1024:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024
    return f"{num:.1f}Yi{suffix}"


class AttachmentError(ValueError):
    """Raised when an attachment is invalid."""


class ParsingError(AttachmentError):
    """Raised when an incoming file cannot be parsed."""


class IllegalPathError(AttachmentError):
    """Raised when an attachment has an illegal path."""


@dataclass
class FileAttachment(Generic[T]):
    """A file attachment."""

    name: str
    content: T

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> FileAttachment:
        """Convert a dict to an attachment."""
        name = data["name"]
        path = Path(name)
        parts = path.parts

        if path.is_absolute() or set(parts[0]) & {"\\", "/"}:
            raise IllegalPathError(f"File path '{name}' must be relative")

        if any(set(part) == {"."} for part in parts):
            raise IllegalPathError(f"File path '{name}' may not use traversal ('..')")

        match data.get("content-encoding"):
            case "base64":
                content = b64decode(data["content"])
            case None | "utf-8" | "":
                content = data["content"].encode("utf-8")
            case _:
                raise ParsingError(f"Unknown content encoding '{data['content-encoding']}'")

        return cls(name, content)

    @classmethod
    def from_path(cls, file: Path, max_size: int | None = None) -> FileAttachment[bytes]:
        """Create an attachment from a file path."""
        size = file.stat().st_size
        if max_size is not None and size > max_size:
            raise AttachmentError(
                f"File {file.name} too large: {sizeof_fmt(size)} "
                f"exceeds the limit of {sizeof_fmt(max_size)}"
            )
        return cls(file.name, file.read_bytes())

    @property
    def size(self) -> int:
        """Size of the attachment."""
        return len(self.content)

    def as_bytes(self) -> bytes:
        """Return the attachment as bytes."""
        if isinstance(self.content, bytes):
            return self.content
        return self.content.encode("utf-8")

    def save_to(self, directory: Path) -> None:
        """Save the attachment to a path directory."""
        file = Path(directory, self.name)
        # Create directories if they don't exist
        file.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(self.content, str):
            file.write_text(self.content, encoding="utf-8")
        else:
            file.write_bytes(self.content)

    def to_dict(self) -> dict[str, str]:
        """Convert the attachment to a dict."""
        comp = zlib.compress(self.as_bytes())
        content = b64encode(comp).decode("ascii")

        return {
            "name": self.name,
            "size": self.size,
            "content-encoding": "base64+zlib",
            "content": content,
        }
