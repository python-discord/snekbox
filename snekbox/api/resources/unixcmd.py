import logging

import falcon
from falcon.media.validators.jsonschema import validate

from snekbox.nsjail import NsJail

log = logging.getLogger(__name__)


class UnixCmdResource:
    """
    Evaluation of Unix commands.

    Supported methods:

    - POST /eval
        Evaluate Unix command in bash and return the result
    """

    REQ_SCHEMA = {
        "type": "object",
        "properties": {
            "input": {
                "type": "string"
            }
        },
        "required": [
            "input"
        ]
    }

    def __init__(self):
        self.nsjail = NsJail()

    @validate(REQ_SCHEMA)
    def on_post(self, req: falcon.Request, resp: falcon.Response) -> None:
        """
        Evaluate Unix commands in a bash shell and return stdout, stderr, and the return code.

        The return code is that of the bash shell.
        Commonly, bash returns the return code of the last executed command.

        Some noteworthy exceptions:

        - None
            The NsJail process failed to launch. This will happen if LinuxFS is not set up.
        - 137 (SIGKILL)
            Typically because NsJail killed the shell process due to time or memory constraints
        - 255
            NsJail encountered a fatal error

        Request body:

        >>> {
        ...     "input": "echo $((1 + 1))"
        ... }

        Response format:

        >>> {
        ...     "stdout": "2\\n",
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

        try:
            result = self.nsjail.unix(code)
        except Exception:
            log.exception("An exception occurred while trying to process the request")
            raise falcon.HTTPInternalServerError

        resp.media = {
            "stdout": result.stdout,
            "returncode": result.returncode
        }
