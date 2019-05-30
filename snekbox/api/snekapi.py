import falcon

from .middleware import LoggingMiddleware
from .resources import EvalResource


class SnekAPI(falcon.API):
    """
    The main entry point to the Falcon application for the snekbox API.

    Routes:

    - /eval
        Evaluation of Python code
    """

    def __init__(self, *args, **kwargs):
        super().__init__(middleware=[LoggingMiddleware()], *args, **kwargs)

        self.add_route("/eval", EvalResource())
