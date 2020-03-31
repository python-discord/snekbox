from .test_eval import TestEvalResource


# `/eval` and `/unixcmd` should be kept the same, so tests should also be the same
class TestUnixCmdResource(TestEvalResource):
    PATH = "/unixcmd"
