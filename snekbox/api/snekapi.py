import falcon

from snekbox.api.resources import EvalResource, InformationResource
from snekbox.nsjail import NsJail


class SnekAPI(falcon.App):
    """
    The main entry point to the snekbox JSON API.

    Forward arguments to a new `NsJail` object.

    Routes:

    - /eval
        Evaluation of Python code

    Error response format:

    >>> {
    ...     "title": "415 Unsupported Media Type",
    ...     "description": "application/xml is an unsupported media type."
    ... }
    """

    def __init__(self, *args, **kwargs):
        super().__init__()

        nsjail = NsJail(*args, **kwargs)
        self.add_route("/eval", EvalResource(nsjail))
        self.add_route("/info", InformationResource())
