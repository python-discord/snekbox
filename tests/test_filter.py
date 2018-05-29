import unittest
import pytest

from snekbox import Snekbox
snek = Snekbox()

class test_filters(unittest.TestCase):

    @pytest.mark.dependency()
    def test_load_filter(self):
        result = snek.load_filter()
        self.assertIsInstance(result, dict)

    @pytest.mark.dependency(depends=["test_filters::test_load_filter"])
    def test_regex_compilation(self):
        filters = snek.load_filter()

        for rule in filters.get('filter'):
            if 'regex' in rule.get('type'):
                print(rule.get('example'))
                print(rule.get('name'))
                match = snek.match_pattern(rule.get('example'), rule.get('name'))
                print(match)
                self.assertIn(rule.get('example'), match)

    @pytest.mark.dependency(depends=["test_filters::test_regex_compilation"])
    def test_security_filter_(self):
        sample_code = "import os"
        result = snek.security_filter(sample_code)

        self.assertFalse(result)
