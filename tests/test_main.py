import contextlib
import io
import unittest
from argparse import Namespace
from subprocess import CompletedProcess
from unittest.mock import patch

import snekbox.__main__ as snekbox_main


class ArgParseTests(unittest.TestCase):
    def test_parse_args(self):
        subtests = (
            (
                ["", "code"],
                Namespace(code="code", nsjail_args=[], py_args=["-c"])
            ),
            (
                ["", "code", "--time_limit", "0"],
                Namespace(code="code", nsjail_args=["--time_limit", "0"], py_args=["-c"])
            ),
            (
                ["", "code", "---", "-m", "timeit"],
                Namespace(code="code", nsjail_args=[], py_args=["-m", "timeit"])
            ),
            (
                ["", "code", "--time_limit", "0", "---", "-m", "timeit"],
                Namespace(code="code", nsjail_args=["--time_limit", "0"], py_args=["-m", "timeit"])
            ),
            (
                ["", "code", "--time_limit", "0", "---"],
                Namespace(code="code", nsjail_args=["--time_limit", "0"], py_args=[])
            ),
            (
                ["", "code", "---"],
                Namespace(code="code", nsjail_args=[], py_args=[])
            )
        )

        for argv, expected in subtests:
            with self.subTest(argv=argv, expected=expected), patch("sys.argv", argv):
                args = snekbox_main.parse_args()
                self.assertEqual(args, expected)

    @patch("sys.argv", [""])
    def test_parse_args_code_missing_exits(self):
        with self.assertRaises(SystemExit) as cm:
            with contextlib.redirect_stderr(io.StringIO()) as stderr:
                snekbox_main.parse_args()

        self.assertEqual(cm.exception.code, 2)
        self.assertIn("the following arguments are required: code", stderr.getvalue())


class EntrypointTests(unittest.TestCase):
    @patch("sys.argv", ["", "code"])
    @patch("snekbox.__main__.NsJail", autospec=True)
    def test_main_prints_stdout(self, mock_nsjail):
        mock_nsjail.return_value.python3.return_value = CompletedProcess(
            args=[],
            returncode=0,
            stdout="output",
            stderr=None
        )

        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            snekbox_main.main()

        self.assertEqual(stdout.getvalue(), "output\n")

    @patch("sys.argv", ["", "code"])
    @patch("snekbox.__main__.NsJail", autospec=True)
    def test_main_exits_with_returncode(self, mock_nsjail):
        mock_nsjail.return_value.python3.return_value = CompletedProcess(
            args=[],
            returncode=137,
            stdout="output",
            stderr=None
        )

        with self.assertRaises(SystemExit) as cm:
            snekbox_main.main()

        self.assertEqual(cm.exception.code, 137)

    @patch("sys.argv", ["", "code", "--time_limit", "0", "---", "-m", "timeit"])
    @patch("snekbox.__main__.NsJail", autospec=True)
    def test_main_forwards_args(self, mock_nsjail):
        mock_nsjail.return_value.python3.return_value = CompletedProcess(
            args=[],
            returncode=0,
            stdout="output",
            stderr=None
        )

        snekbox_main.main()

        mock_nsjail.return_value.python3.assert_called_once_with(
            "code", nsjail_args=["--time_limit", "0"], py_args=["-m", "timeit"]
        )
