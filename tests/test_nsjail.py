import logging
import unittest
from textwrap import dedent

from snekbox.nsjail import NsJail


class NsJailTests(unittest.TestCase):
    def setUp(self):
        super().setUp()

        self.nsjail = NsJail()
        self.logger = logging.getLogger("snekbox.nsjail")

    def test_print_returns_0(self):
        result = self.nsjail.python3("print('test')")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "test\n")
        self.assertEqual(result.stderr, None)

    def test_timeout_returns_137(self):
        code = dedent("""
            x = '*'
            while True:
                try:
                    x = x * 99
                except:
                    continue
        """).strip()

        with self.assertLogs(self.logger) as log:
            result = self.nsjail.python3(code)

        self.assertEqual(result.returncode, 137)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, None)
        self.assertIn("run time >= time limit", "\n".join(log.output))

    def test_subprocess_resource_unavailable(self):
        code = dedent("""
            import subprocess
            print(subprocess.check_output('kill -9 6', shell=True).decode())
        """).strip()

        result = self.nsjail.python3(code)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Resource temporarily unavailable", result.stdout)
        self.assertEqual(result.stderr, None)

    def test_forkbomb_resource_unavailable(self):
        code = dedent("""
            import os
            while 1:
                os.fork()
        """).strip()

        result = self.nsjail.python3(code)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Resource temporarily unavailable", result.stdout)
        self.assertEqual(result.stderr, None)

    def test_sigsegv_returns_139(self):  # In honour of Juan.
        code = dedent("""
            import ctypes
            ctypes.string_at(0)
        """).strip()

        result = self.nsjail.python3(code)
        self.assertEqual(result.returncode, 139)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, None)

    def test_null_byte_value_error(self):
        result = self.nsjail.python3("\0")
        self.assertEqual(result.returncode, None)
        self.assertEqual(result.stdout, "ValueError: embedded null byte")
        self.assertEqual(result.stderr, None)
