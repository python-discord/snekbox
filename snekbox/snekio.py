from __future__ import annotations

import mimetypes
from base64 import b64encode
from dataclasses import dataclass
from pathlib import Path

SUPPORTED_MIME_TYPES = {
    "image/png",
    "image/jpeg",
}


class AttachmentError(ValueError):
    """Raised when an attachment is invalid."""


@dataclass
class FileAttachment:
    """A file attachment."""

    name: str
    content: bytes

    @classmethod
    def from_path(cls, path: Path, max_size: int) -> FileAttachment:
        """Create an attachment from a path."""
        with path.open("rb") as f:
            content = f.read(max_size + 1)
            if len(content) > max_size:
                raise AttachmentError(f"File too large: {path}")
        return cls(path.name, content)

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
