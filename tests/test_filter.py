import unittest
import pytest
import yaml

from snekbox import Snekbox
snek = Snekbox()

class test_filters(unittest.TestCase):
    def test_regex_failure(self):
        """ Ensure exceptions are raised if regex cannot compile """
        with self.assertRaises(Exception):
            snek.match_pattern('test', '+++309345+09´´+0`?`?=')

    @pytest.mark.dependency()
    def test_load_filter(self):
        """ ensure the filter.yml file is valid yaml """
        result = snek.load_filter()
        self.assertIsInstance(result, dict)

    @pytest.mark.dependency(depends=["test_filters::test_load_filter"])
    def test_regex_compilation(self):
        """ test every filter regex against code examples """
        filters = snek.load_filter()

        for rule in filters.get('filter'):
            if 'regex' in rule.get('type'):
                for example in rule.get('example'):
                    match = snek.match_pattern(example, rule.get('name'))
                    self.assertIn(example, match)

    @pytest.mark.dependency(depends=["test_filters::test_regex_compilation"])
    def test_security_filter_(self):
        """ ensure the abstraction function works """
        sample_code = "import os"
        result = snek.security_filter(sample_code)

        self.assertFalse(result)
