import logging

import falcon
from falcon.media.validators.jsonschema import validate

from snekbox.nsjail import NsJail

log = logging.getLogger(__name__)


class EvalResource:
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
