import unittest

from snekbox.nsjail import NsJail

nsjail = NsJail()


class SnekTests(unittest.TestCase):
    def test_nsjail(self):
        result = nsjail.python3('print("test")')
        self.assertEquals(result.strip(), 'test')

    # def test_memory_error(self):
    #     code = ('x = "*"\n'
    #             'while True:\n'
    #             '    x = x * 99\n')
    #     result = nsjail.python3(code)
    #     self.assertEquals(result.strip(), 'timed out or memory limit exceeded')

    def test_timeout(self):
        code = (
            'x = "*"\n'
            'while True:\n'
            '    try:\n'
            '        x = x * 99\n'
            '    except:\n'
            '        continue\n'
        )

        result = nsjail.python3(code)
        self.assertEquals(result.strip(), 'timed out or memory limit exceeded')

    def test_kill(self):
        code = ('import subprocess\n'
                'print(subprocess.check_output("kill -9 6", shell=True).decode())')
        result = nsjail.python3(code)
        if 'ModuleNotFoundError' in result.strip():
            self.assertIn('ModuleNotFoundError', result.strip())
        else:
            self.assertIn('(PIDs left: 0)', result.strip())

    def test_forkbomb(self):
        code = ('import os\n'
                'while 1:\n'
                '    os.fork()')
        result = nsjail.python3(code)
        self.assertIn('Resource temporarily unavailable', result.strip())

    def test_juan_golf(self):  # in honour of Juan
        code = ("func = lambda: None\n"
                "CodeType = type(func.__code__)\n"
                "bytecode = CodeType(0,1,0,0,0,b'',(),(),(),'','',1,b'')\n"
                "exec(bytecode)")

        result = nsjail.python3(code)
        self.assertEquals('unknown error, code: 111', result.strip())
