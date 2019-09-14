import falcon

from .resources import EvalResource


class SnekAPI(falcon.API):
    """
    The main entry point to the snekbox JSON API.

    Routes:

    - /eval
        Evaluation of Python code

    Error response format:

    >>> {
    ...     "title": "Unsupported media type",
    ...     "description": "application/xml is an unsupported media type."
    ... }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.add_route("/eval", EvalResource())
