from __future__ import annotations

import mimetypes
import zlib
from base64 import b64encode
from dataclasses import dataclass
from pathlib import Path


def sizeof_fmt(num: int, suffix: str = "B") -> str:
    """Return a human-readable file size."""
    for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"):
        if abs(num) < 1024:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024
    return f"{num:.1f}Yi{suffix}"


class AttachmentError(ValueError):
    """Raised when an attachment is invalid."""


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
    def mime(self) -> str:
        """MIME type of the attachment."""
        return mimetypes.guess_type(self.name)[0]

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
            "mime": self.mime,
            "size": self.size,
            "compression": "zlib",
            "content": content,
        }
