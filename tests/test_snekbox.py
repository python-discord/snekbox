import unittest
import pytest
import os
import json

from snekbox import Snekbox
from rmq import Rmq

r = Rmq()

snek = Snekbox()


class SnekTests(unittest.TestCase):
    def test_nsjail(self):
        result = snek.python3('print("test")')
        self.assertEquals(result.strip(), 'test')

    def test_memory_error(self):
        code = ('x = "*"\n'
                'while True:\n'
                '    x = x * 99\n')

        result = snek.python3(code)
        self.assertEquals(result.strip(), 'timed out or memory limit exceeded')

    def test_timeout(self):
        code = ('x = "*"\n'
        'while True:\n'
        '    try:\n'
        '        x = x * 99\n'
        '    except:\n'
        '        continue\n')

        result = snek.python3(code)
        self.assertEquals(result.strip(), 'timed out or memory limit exceeded')

    def test_kill(self):
        code = ('import subprocess\n'
                'print(subprocess.check_output("kill -9 6", shell=True).decode())')
        result = snek.python3(code)
        if 'ModuleNotFoundError' in result.strip():
            self.assertIn('ModuleNotFoundError', result.strip())
        else:
            self.assertIn('(PIDs left: 0)', result.strip())

    def test_forkbomb(self):
        code = ('import os\n'
                'while 1:\n'
                '    os.fork()')
        result = snek.python3(code)
        self.assertIn('(PIDs left: 0)', result.strip())


class RMQTests(unittest.TestCase):
    @pytest.mark.dependency()
    def test_a_publish(self):
        message = json.dumps({"snekid": "test", "message": "print('test')"})
        result = r.publish(message)
        self.assertTrue(result)

    @pytest.mark.dependency(depends=["RMQTests::test_a_publish"])
    def test_b_consume(self):
        result = r.consume(callback=snek.message_handler, queue='input', run_once=True)
        self.assertEquals(result[2], b'{"snekid": "test", "message": "print(\'test\')"}')
