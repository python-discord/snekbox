import logging

import falcon
from falcon.media.validators.jsonschema import validate

from snekbox.nsjail import NsJail

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
    def on_post(self, req, resp):
        """
        Evaluate Python code and return the result.

        Request body:

        >>> {
        ...     "input": "print(1 + 1)"
        ... }

        Response format:

        >>> {
        ...     "input": "print(1 + 1)",
        ...     "output": "2\\n"
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
            output = self.nsjail.python3(code)
        except Exception:
            log.exception("An exception occurred while trying to process the request")
            raise falcon.HTTPInternalServerError

        resp.media = {
            "input": code,
            "output": output
        }
