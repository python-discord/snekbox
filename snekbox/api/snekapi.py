import falcon

from .resources import EvalResource


class SnekAPI(falcon.API):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.add_route("/eval", EvalResource())
