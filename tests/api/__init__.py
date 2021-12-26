import logging
from subprocess import CompletedProcess
from unittest import mock

from falcon import testing

from snekbox.api import SnekAPI


class SnekAPITestCase(testing.TestCase):
    def setUp(self):
        super().setUp()

        self.patcher = mock.patch("snekbox.api.resources.eval.NsJail", autospec=True)
        self.mock_nsjail = self.patcher.start()
        self.mock_nsjail.return_value.python3.return_value = CompletedProcess(
            args=[],
            returncode=0,
            stdout="output",
            stderr="error"
        )
        self.addCleanup(self.patcher.stop)

        logging.getLogger("snekbox.nsjail").setLevel(logging.WARNING)

        self.app = SnekAPI()
