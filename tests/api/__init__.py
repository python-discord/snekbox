from subprocess import CompletedProcess
from unittest import mock

from falcon import testing

from snekbox.api import SnekAPI


class SnekAPITestCase(testing.TestCase):
    def setUp(self):
        super().setUp()

        self.python3_patcher = mock.patch("snekbox.api.resources.eval.NsJail", autospec=True)
        self.unix_patcher = mock.patch("snekbox.api.resources.unixcmd.NsJail", autospec=True)

        self.mock_eval_nsjail = self.python3_patcher.start()
        self.mock_unixcmd_nsjail = self.unix_patcher.start()

        mock_process = CompletedProcess(
            args=[],
            returncode=0,
            stdout="output",
            stderr="error"
        )
        self.mock_eval_nsjail.return_value.python3.return_value = mock_process
        self.mock_unixcmd_nsjail.return_value.unix.return_value = mock_process

        self.addCleanup(self.python3_patcher.stop)
        self.addCleanup(self.unix_patcher.stop)

        self.app = SnekAPI()
