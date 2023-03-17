import logging

import falcon
from falcon.media.validators.jsonschema import validate

from scripts.python_version import VERSION_DISPLAY_NAMES

__all__ = ("InformationResource",)

log = logging.getLogger(__name__)


class InformationResource:
    """
    Information about the server.

    Supported methods:

    - GET /info
        Get information about the current server, and supported features.
    """

    RESP_SCHEMA = {
        "versions": {"type": "array", "items": {"type": "str"}},
    }

    @validate(resp_schema=RESP_SCHEMA)
    def on_get(self, _: falcon.Request, resp: falcon.Response) -> None:
        """
        Get information about the server.

        Response format:
        >>> {
        ...     "python_versions": ["CPython 3.10", "pypy 3.9", "CPython 3.12 Beta 1"]
        ... }

        Status codes:

        - 200
            Success.
        """
        resp.media = {
            "python_versions": VERSION_DISPLAY_NAMES,
        }
