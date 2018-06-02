import unittest
import pytest
import os
import json

from snekbox import Snekbox
from rmq import Rmq

r = Rmq()

nsjail = os.sep.join([os.getcwd(), f'binaries{os.sep}nsjail2.6-ubuntu-x86_64'])
snek = Snekbox(nsjail_binary=nsjail)


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


class RMQTests(unittest.TestCase):
	def test_a_publish(self):
		message = json.dumps({"snekid": "test", "message": "print('test')"})
		result = r.publish(message)
		self.assertTrue(result)

	def test_b_consume(self):
		result = r.consume(callback=snek.message_handler, queue='input', run_once=True)
		self.assertEquals(result[2], b'{"snekid": "test", "message": "print(\'test\')"}')
