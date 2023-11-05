import logging
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from unittest import TestCase, mock
from uuid import uuid4

from snekbox.snekio import MemFS

UUID_TEST = uuid4()


class MemFSTests(TestCase):
    def setUp(self):
        super().setUp()
        self.logger = logging.getLogger("snekbox.snekio.memfs")
        self.logger.setLevel(logging.WARNING)

    @mock.patch("snekbox.snekio.memfs.uuid4", lambda: UUID_TEST)
    def test_assignment_thread_safe(self):
        """Test concurrent mounting works in multi-thread environments."""
        # Concurrently create MemFS in threads, check only 1 can be created
        # Others should result in RuntimeError
        with ExitStack() as stack:
            with ThreadPoolExecutor() as executor:
                memfs: MemFS | None = None
                # Each future uses enter_context to ensure __exit__ on test exception
                futures = [
                    executor.submit(lambda: stack.enter_context(MemFS(10))) for _ in range(8)
                ]
                for future in futures:
                    # We should have exactly one result and all others RuntimeErrors
                    if err := future.exception():
                        self.assertIsInstance(err, RuntimeError)
                    else:
                        self.assertIsNone(memfs)
                        memfs = future.result()

                # Original memfs should still exist afterwards
                self.assertIsInstance(memfs, MemFS)
                self.assertTrue(memfs.path.is_mount())

    def test_cleanup(self):
        """Test explicit cleanup."""
        memfs = MemFS(10)
        path = memfs.path
        self.assertTrue(path.is_mount())
        memfs.cleanup()
        self.assertFalse(path.exists())

    def test_context_cleanup(self):
        """Context __exit__ should trigger cleanup."""
        with MemFS(10) as memfs:
            path = memfs.path
            self.assertTrue(path.is_mount())
        self.assertFalse(path.exists())

    def test_implicit_cleanup(self):
        """Test implicit _cleanup triggered by GC."""
        memfs = MemFS(10)
        path = memfs.path
        self.assertTrue(path.is_mount())
        # Catch the warning about implicit cleanup
        with self.assertWarns(ResourceWarning):
            del memfs
        self.assertFalse(path.exists())
