import json
import unittest
import urllib.request
from multiprocessing.dummy import Pool

from tests.gunicorn_utils import run_gunicorn


def run_code_in_snekbox(code: str) -> tuple[str, int]:
    body = {"args": ["-c", code]}
    json_data = json.dumps(body).encode("utf-8")

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
                results = p.map(run_code_in_snekbox, args)

            responses, statuses = zip(*results)

            self.assertTrue(all(status == 200 for status in statuses))
            self.assertTrue(all(json.loads(response)["returncode"] == 0 for response in responses))
