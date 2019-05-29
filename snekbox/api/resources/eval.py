import logging

import falcon

from snekbox.nsjail import NsJail

log = logging.getLogger(__name__)


class EvalResource:
    def __init__(self):
        self.nsjail = NsJail()

    def on_post(self, req, resp):
        code = req.media.get("code")

        try:
            output = self.nsjail.python3(code)
        except Exception:
            log.exception("An exception occurred while trying to process the request")
            raise falcon.HTTPInternalServerError

        resp.media = {
            "input": code,
            "output": output
        }
