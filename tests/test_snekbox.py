import unittest
import pytest
import os

from snekbox import Snekbox
python_binary = os.environ.get('PYTHONEXECUTABLE', '/usr/bin/python3.6')
nsjail = os.sep.join([os.getcwd(), f'binaries{os.sep}nsjail2.6-ubuntu-x86_64'])
snek = Snekbox(nsjail_binary=nsjail, python_binary=python_binary)

class SnekTests(unittest.TestCase):
	def test_nsjail(self):
		result = snek.python3('print("test")')
		self.assertEquals(result.strip(), 'test')

	def test_memory_error(self):
		code = ('x = "*"\n'
			    'while True:\n'
			    '    x = x * 99\n')

		result = snek.python3(code)
		self.assertEquals(result.strip(), 'MemoryError')

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
			self.assertIn('returned non-zero exit status 1.', result.strip())
