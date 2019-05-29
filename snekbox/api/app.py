import falcon

from .resources import EvalResource

api = falcon.API()
api.add_route("/eval", EvalResource())
