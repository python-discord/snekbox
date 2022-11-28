import json
import unittest
import urllib.request
from base64 import b64encode
from multiprocessing.dummy import Pool
from textwrap import dedent

from tests.gunicorn_utils import run_gunicorn


def b64encode_code(data: str):
    data = dedent(data).strip()
    return b64encode(data.encode()).decode("ascii")


def snekbox_run_code(code: str) -> tuple[str, int]:
    body = {"args": ["-c", code]}
    return snekbox_request(body)


def snekbox_request(content: dict) -> tuple[str, int]:
    json_data = json.dumps(content).encode("utf-8")

    req = urllib.request.Request("http://localhost:8060/eval")
    req.add_header("Content-Type", "application/json; charset=utf-8")
    req.add_header("Content-Length", str(len(json_data)))

    with urllib.request.urlopen(req, json_data, timeout=30) as response:
        response_data = response.read().decode("utf-8")

    return response_data, response.status


class IntegrationTests(unittest.TestCase):
    def test_memory_limit_separate_per_process(self):
        """
        Each NsJail process should have its own memory limit.

        The memory used by one process should not contribute to the memory cap of other processes.
        See https://github.com/python-discord/snekbox/issues/83
        """
        with run_gunicorn():
            code = "import time; ' ' * 33000000; time.sleep(0.1)"
            processes = 3

            args = [code] * processes
            with Pool(processes) as p:
                results = p.map(snekbox_run_code, args)

            responses, statuses = zip(*results)

            self.assertTrue(all(status == 200 for status in statuses))
            self.assertTrue(all(json.loads(response)["returncode"] == 0 for response in responses))

    def test_eval(self):
        """Test normal eval requests without files."""
        with run_gunicorn():
            cases = [
                ({"input": "print('Hello')"}, "Hello"),
                ({"args": ["-c", "print('Hello')"]}, "Hello"),
            ]
            for body, expected in cases:
                with self.subTest(body=body):
                    response, status = snekbox_request(body)
                    self.assertEqual(status, 200)
                    self.assertEqual(json.loads(response)["stdout"], expected)

    def test_files_send_receive(self):
        """Test sending and receiving files to snekbox."""
        with run_gunicorn():
            request = {
                "args": ["main.py"],
                "files": [
                    {
                        "path": "main.py",
                        "content": b64encode_code(
                            """
                            from pathlib import Path
                            from mod import lib
                            print(lib.var)

                            with open('output/test.txt', 'w') as f:
                                f.write('test 1')

                            Path('output/dir').mkdir()
                            Path('output/dir/test2.txt').write_text('test 2')
                            """
                        ),
                    },
                    {"path": "mod/__init__.py"},
                    {"path": "mod/lib.py", "content": b64encode_code("var = 'hello'")},
                ],
            }

            expected = {
                "stdout": "hello\n",
                "returncode": 0,
                "files": [
                    {
                        "path": "dir/test2.txt",
                        "size": len("test 2"),
                        "content": b64encode_code("test 2"),
                    },
                    {
                        "path": "test.txt",
                        "size": len("test 1"),
                        "content": b64encode_code("test 1"),
                    },
                ],
            }

            response, status = snekbox_request(request)

            self.assertEqual(200, status)
            self.assertEqual(expected, json.loads(response))
