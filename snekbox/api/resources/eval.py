import logging

import falcon
from falcon.media.validators.jsonschema import validate

from snekbox.nsjail import NsJail

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
        },
        "required": ["input"],
    }

    def __init__(self, nsjail: NsJail):
        self.nsjail = nsjail

    @validate(REQ_SCHEMA)
    def on_post(self, req: falcon.Request, resp: falcon.Response) -> None:
        """
        Evaluate Python code and return stdout, stderr, and the return code.

        A list of arguments for the Python subprocess can be specified as `args`.
        Otherwise, the default argument "-c" is used to execute the input code.
        The input code is always passed as the last argument to Python.

        The return codes mostly resemble those of a Unix shell. Some noteworthy cases:

        - None
            The NsJail process failed to launch or the output was invalid Unicode
        - 137 (SIGKILL)
            Typically because NsJail killed the Python process due to time or memory constraints
        - 255
            NsJail encountered a fatal error

        Request body:

        >>> {
        ...     "input": "[i for i in range(1000)]",
        ...     "args": ["-m", "timeit"] # This is optional
        ... }

        Response format:

        >>> {
        ...     "stdout": "10000 loops, best of 5: 23.8 usec per loop\n",
        ...     "returncode": 0
        ... }

        Status codes:

        - 200
            Successful evaluation; not indicative that the input code itself works
        - 400
           Input's JSON schema is invalid
        - 415
            Unsupported content type; only application/JSON is supported
        """
        code = req.media["input"]
        args = req.media.get("args", ("",))

        try:
            result = self.nsjail.python3(code, py_args=args)
        except Exception:
            log.exception("An exception occurred while trying to process the request")
            raise falcon.HTTPInternalServerError

        resp.media = {
            "stdout": result.stdout,
            "returncode": result.returncode,
            "attachments": [atc.to_dict() for atc in result.attachments],
        }
