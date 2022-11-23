import logging
from concurrent.futures import ThreadPoolExecutor
from unittest import TestCase, mock
from uuid import uuid4

from snekbox.memfs import MemFS

UUID_TEST = uuid4()


def get_memfs_with_context():
    return MemFS(10).__enter__()


class NsJailTests(TestCase):
    def setUp(self):
        super().setUp()
        self.logger = logging.getLogger("snekbox.memfs")
        self.logger.setLevel(logging.WARNING)

    @mock.patch("snekbox.memfs.uuid4", lambda: UUID_TEST)
    def test_assignment_thread_safe(self):
        """Test concurrent mounting works in multi-thread environments."""
        # Concurrently create MemFS in threads, check only 1 can be created
        # Others should result in RuntimeError
        with ThreadPoolExecutor() as pool:
            memfs: MemFS | None = None
            futures = [pool.submit(get_memfs_with_context) for _ in range(8)]
            for future in futures:
                # We should have exactly one result and all others RuntimeErrors
                if err := future.exception():
                    self.assertIsInstance(err, RuntimeError)
                else:
                    self.assertIsNone(memfs)
                    memfs = future.result()

            # Original memfs should still exist afterwards
            self.assertIsInstance(memfs, MemFS)
            self.assertTrue(memfs.path.exists())
