from __future__ import annotations

import logging

import falcon
from falcon.media.validators.jsonschema import validate

from snekbox.nsjail import NsJail

__all__ = ("EvalResource",)

from snekbox.snekio import FileAttachment, ParsingError

log = logging.getLogger(__name__)


class EvalResource:
    """
    Evaluation of Python code.

    Supported methods:

    - POST /eval
        Evaluate Python code and return the result
    """

    REQ_SCHEMA = {
        "type": "object",
        "properties": {
            "args": {"type": "array", "items": {"type": "string"}},
            "files": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "content-encoding": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["name"],
                },
            },
        },
        "required": ["args"],
    }

    def __init__(self, nsjail: NsJail):
        self.nsjail = nsjail

    @validate(REQ_SCHEMA)
    def on_post(self, req: falcon.Request, resp: falcon.Response) -> None:
        """
        Evaluate Python code and return stdout, stderr, and the return code.

        A list of arguments for the Python subprocess can be specified as `args`.

        The return codes mostly resemble those of a Unix shell. Some noteworthy cases:

        - None
            The NsJail process failed to launch or the output was invalid Unicode
        - 137 (SIGKILL)
            Typically because NsJail killed the Python process due to time or memory constraints
        - 255
            NsJail encountered a fatal error

        Request body:

        >>> {
        ...    "args": ["-c", "print('Hello')"]
        ... }

        >>> {
        ...    "args": ["main.py"],
        ...    "files": [
        ...        {
        ...            "name": "main.py",
        ...            "content": "print(1)"
        ...        }
        ...    ]
        ... }

        Response format:

        >>> {
        ...     "stdout": "10000 loops, best of 5: 23.8 usec per loop",
        ...     "returncode": 0,
        ...     "attachments": [
        ...         {
        ...             "name": "output.png",
        ...             "mime": "image/png",
        ...             "size": 57344,
        ...             "compression": "zlib",
        ...             "content": "eJzzSM3...="  # Base64-encoded
        ...         }
        ...     ]
        ... }

        Status codes:

        - 200
            Successful evaluation; not indicative that the input code itself works
        - 400
           Input JSON schema is invalid
        - 415
            Unsupported content type; only application/JSON is supported
        """
        try:
            result = self.nsjail.python3(
                py_args=req.media["args"],
                files=[FileAttachment.from_dict(file) for file in req.media.get("files", [])],
            )
        except ParsingError as e:
            raise falcon.HTTPBadRequest(description=f"Invalid file in request: {e}")
        except Exception:
            log.exception("An exception occurred while trying to process the request")
            raise falcon.HTTPInternalServerError

        resp.media = {
            "stdout": result.stdout,
            "returncode": result.returncode,
            "attachments": [atc.to_dict() for atc in result.attachments],
        }
