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
