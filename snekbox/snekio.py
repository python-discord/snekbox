from __future__ import annotations

import zlib
from base64 import b64encode
from dataclasses import dataclass
from pathlib import Path

RequestType = dict[str, str | bool | list[str | dict[str, str]]]


def sizeof_fmt(num: int, suffix: str = "B") -> str:
    """Return a human-readable file size."""
    for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"):
        if abs(num) < 1024:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024
    return f"{num:.1f}Yi{suffix}"


class AttachmentError(ValueError):
    """Raised when an attachment is invalid."""


class FileParsingError(ValueError):
    """Raised when a request file cannot be parsed."""


@dataclass
class EvalRequestFile:
    """A file sent in an eval request."""

    name: str
    content: str

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> EvalRequestFile:
        """Convert a dict to a str attachment."""
        name = data["name"]
        path = Path(name)
        parts = path.parts

        if path.is_absolute() or set(parts[0]) & {"\\", "/"}:
            raise FileParsingError(f"File path '{name}' must be relative")

        if any(set(part) == {"."} for part in parts):
            raise FileParsingError(f"File path '{name}' may not use traversal ('..')")

        return cls(name, data.get("content", ""))

    def save_to(self, directory: Path) -> None:
        """Save the attachment to a path directory."""
        file = Path(directory, self.name)
        # Create directories if they don't exist
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(self.content)


@dataclass
class FileAttachment:
    """A file attachment."""

    name: str
    content: bytes

    @classmethod
    def from_path(cls, file: Path, max_size: int | None = None) -> FileAttachment:
        """Create an attachment from a path."""
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

    def to_dict(self) -> dict[str, str]:
        """Convert the attachment to a dict."""
        cmp = zlib.compress(self.content)
        content = b64encode(cmp).decode("ascii")
        return {
            "name": self.name,
            "size": self.size,
            "content": content,
        }
