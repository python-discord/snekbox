from __future__ import annotations

import mimetypes
from base64 import b64encode
from dataclasses import dataclass
from pathlib import Path

SUPPORTED_MIME_TYPES = {
    "image/png",
    "image/jpeg",
}


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
    def from_path(cls, file: Path, max_size: int) -> FileAttachment:
        """Create an attachment from a path."""
        size = file.stat().st_size
        if size > max_size:
            raise AttachmentError(
                f"File {file.name} too large: {sizeof_fmt(size)} "
                f"exceeds the limit of {sizeof_fmt(max_size)}"
            )

        with file.open("rb") as f:
            content = f.read(max_size + 1)
            size = len(content)
            if len(content) > max_size:
                raise AttachmentError(
                    f"File {file.name} too large: {sizeof_fmt(len(content))} "
                    f"exceeds the limit of {sizeof_fmt(max_size)}"
                )
        return cls(file.name, content)

    @property
    def mime(self) -> str:
        """MIME type of the attachment."""
        return mimetypes.guess_type(self.name)[0]

    def is_supported(self) -> bool:
        """Return whether the attachment is supported."""
        if self.mime.startswith("text/"):
            return True
        return self.mime in SUPPORTED_MIME_TYPES

    def to_dict(self) -> dict[str, str]:
        """Convert the attachment to a dict."""
        return {"name": self.name, "mime": self.mime, "content": b64encode(self.content).decode()}
