from __future__ import annotations

import logging

import falcon
from falcon.media.validators.jsonschema import validate

from snekbox.nsjail import NsJail
from snekbox.snekio import FileAttachment, ParsingError

__all__ = ("EvalResource",)

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
            "input": {"type": "string"},
            "args": {"type": "array", "items": {"type": "string"}},
            "files": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            # Disallow starting with / or containing \0 anywhere
                            "pattern": r"^(?!/)(?!.*\\0).*$",
                        },
                        "content": {"type": "string"},
                    },
                    "required": ["path"],
                },
            },
        },
        "anyOf": [
            {"required": ["input"]},
            {"required": ["args"]},
        ],
    }

    def __init__(self, nsjail: NsJail):
        self.nsjail = nsjail

    @validate(REQ_SCHEMA)
    def on_post(self, req: falcon.Request, resp: falcon.Response) -> None:
        """
        Evaluate Python code and return stdout, stderr, and the return code.

        A list of arguments for the Python subprocess can be specified as `args`.

        If `input` is specified, it will be appended as the last argument to `args`,
        and `args` will have a default argument of `"-c"`.

        Either `input` or `args` must be specified.

        The return codes mostly resemble those of a Unix shell. Some noteworthy cases:

        - None
            The NsJail process failed to launch or the output was invalid Unicode
        - 137 (SIGKILL)
            Typically because NsJail killed the Python process due to time or memory constraints
        - 255
            NsJail encountered a fatal error

        Request body:

        >>> {
        ...    "input": "print('Hello')"
        ... }

        >>> {
        ...    "args": ["-c", "print('Hello')"]
        ... }

        >>> {
        ...    "args": ["main.py"],
        ...    "files": [
        ...        {
        ...            "path": "main.py",
        ...            "content": "SGVsbG8...="  # Base64
        ...        }
        ...    ]
        ... }

        Response format:

        >>> {
        ...     "stdout": "10000 loops, best of 5: 23.8 usec per loop",
        ...     "returncode": 0,
        ...     "files": [
        ...         {
        ...             "path": "output.png",
        ...             "size": 57344,
        ...             "content": "eJzzSM3...="  # Base64
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
        body: dict[str, str | list[str] | list[dict[str, str]]] = req.media
        # If `input` is supplied, default `args` to `-c`
        if "input" in body:
            body.setdefault("args", ["-c"])
            body["args"].append(body["input"])
        try:
            result = self.nsjail.python3(
                py_args=body["args"],
                files=[FileAttachment.from_dict(file) for file in body.get("files", [])],
            )
        except ParsingError as e:
            raise falcon.HTTPBadRequest(title="Request file is invalid", description=str(e))
        except Exception:
            log.exception("An exception occurred while trying to process the request")
            raise falcon.HTTPInternalServerError

        resp.media = {
            "stdout": result.stdout,
            "returncode": result.returncode,
            "files": [f.as_dict for f in result.files],
        }
