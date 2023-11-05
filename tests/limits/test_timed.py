import math
import time
from unittest import TestCase

from snekbox.limits.timed import time_limit


class TimedTests(TestCase):
    def test_sleep(self):
        """Test that a sleep can be interrupted."""
        _finished = False
        start = time.perf_counter()
        with self.assertRaises(TimeoutError):
            with time_limit(1):
                time.sleep(2)
                _finished = True
        end = time.perf_counter()
        self.assertLess(end - start, 2)
        self.assertFalse(_finished)

    def test_iter(self):
        """Test that a long-running built-in function can be interrupted."""
        _result = 0
        start = time.perf_counter()
        with self.assertRaises(TimeoutError):
            with time_limit(1):
                _result = math.factorial(2**30)
        end = time.perf_counter()
        self.assertEqual(_result, 0)
        self.assertLess(end - start, 2)
