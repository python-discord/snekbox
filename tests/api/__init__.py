from unittest import mock

from falcon import testing


class SnekAPITestCase(testing.TestCase):
    def setUp(self):
        super().setUp()

        self.patcher = mock.patch("snekbox.api.resources.eval.NsJail", autospec=True)
        self.mock_nsjail = self.patcher.start()
        self.mock_nsjail.return_value.python3.return_value = "test output"
        self.addCleanup(self.patcher.stop)

        from snekbox.api import SnekAPI
        self.app = SnekAPI()
