from unittest import TestCase

from snekbox import snekio
from snekbox.snekio import FileAttachment, IllegalPathError, ParsingError


class SnekIOTests(TestCase):
    def test_safe_path(self) -> None:
        cases = [
            ("", ""),
            ("foo", "foo"),
            ("foo/bar", "foo/bar"),
            ("foo/bar.ext", "foo/bar.ext"),
        ]

        for path, expected in cases:
            self.assertEqual(snekio.safe_path(path), expected)

    def test_safe_path_raise(self):
        cases = [
            ("../foo", IllegalPathError, "File path '../foo' may not traverse beyond root"),
            ("/foo", IllegalPathError, "File path '/foo' must be relative"),
        ]

        for path, error, msg in cases:
            with self.assertRaises(error) as cm:
                snekio.safe_path(path)
            self.assertEqual(str(cm.exception), msg)

    def test_file_from_dict(self):
        cases = [
            ({"path": "foo", "content": ""}, FileAttachment("foo", b"")),
            ({"path": "foo"}, FileAttachment("foo", b"")),
            ({"path": "foo", "content": "Zm9v"}, FileAttachment("foo", b"foo")),
            ({"path": "foo/bar.ext", "content": "Zm9v"}, FileAttachment("foo/bar.ext", b"foo")),
        ]

        for data, expected in cases:
            self.assertEqual(FileAttachment.from_dict(data), expected)

    def test_file_from_dict_error(self):
        cases = [
            (
                {"path": "foo", "content": "9"},
                ParsingError,
                "Invalid base64 encoding for file 'foo'",
            ),
            (
                {"path": "var/a.txt", "content": "1="},
                ParsingError,
                "Invalid base64 encoding for file 'var/a.txt'",
            ),
        ]

        for data, error, msg in cases:
            with self.assertRaises(error) as cm:
                FileAttachment.from_dict(data)
            self.assertEqual(str(cm.exception), msg)
