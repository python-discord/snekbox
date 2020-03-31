import logging
import unittest

from snekbox.nsjail import NsJail


class NsJailTestCase(unittest.TestCase):
    def setUp(self):
        super().setUp()

        self.nsjail = NsJail()
        self.nsjail.DEBUG = False
        self.logger = logging.getLogger("snekbox.nsjail")
