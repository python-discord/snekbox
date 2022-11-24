from contextlib import contextmanager
from pathlib import Path
from unittest import TestCase
from uuid import uuid4

from snekbox import libmount


class LibMountTests(TestCase):
    def setUp(self):
        self.temp_dir = Path("/tmp/snekbox-test")
        self.temp_dir.mkdir(exist_ok=True, parents=True)
        super().setUp()

    @contextmanager
    def get_mount(self):
        """Yields a valid mount point, unmounts after context."""
        path = self.temp_dir / str(uuid4())
        path.mkdir()
        try:
            libmount.mount(source="", target=path, fs="tmpfs")
            yield path
        finally:
            libmount.unmount(target=path)

    def test_mount(self):
        """Test normal mounting."""
        with self.get_mount() as path:
            self.assertTrue(path.is_mount())
            self.assertTrue(path.exists())
        self.assertFalse(path.is_mount())
        # Unmounting should not remove the original folder
        self.assertTrue(path.exists())

    def test_mount_errors(self):
        """Test invalid mount errors."""
        cases = [
            (dict(source="", target=str(uuid4()), fs="tmpfs"), OSError, "No such file"),
            (dict(source=str(uuid4()), target="some/dir", fs="tmpfs"), OSError, "No such file"),
            (
                dict(source="", target=self.temp_dir, fs="tmpfs", invalid_opt="?"),
                OSError,
                "Invalid argument",
            ),
        ]
        for case, err, msg in cases:
            with self.subTest(case=case):
                with self.assertRaises(err) as cm:
                    libmount.mount(**case)
                self.assertIn(msg, str(cm.exception))

    def test_mount_duplicate(self):
        """Test attempted mount after mounted."""
        path = self.temp_dir / str(uuid4())
        path.mkdir()
        try:
            libmount.mount(source="", target=path, fs="tmpfs")
            with self.assertRaises(OSError) as cm:
                libmount.mount(source="", target=path, fs="tmpfs")
            self.assertIn("already a mount point", str(cm.exception))
        finally:
            libmount.unmount(target=path)

    def test_unmount_errors(self):
        """Test invalid unmount errors."""
        cases = [
            (dict(target="not/exist"), OSError, "is not a mount point"),
            (dict(target=Path("not/exist")), OSError, "is not a mount point"),
        ]
        for case, err, msg in cases:
            with self.subTest(case=case):
                with self.assertRaises(err) as cm:
                    libmount.unmount(**case)
                self.assertIn(msg, str(cm.exception))

    def test_unmount_invalid_args(self):
        """Test invalid unmount invalid flag."""
        with self.get_mount() as path:
            with self.assertRaises(OSError) as cm:
                libmount.unmount(path, 251)
            self.assertIn("Invalid argument", str(cm.exception))
