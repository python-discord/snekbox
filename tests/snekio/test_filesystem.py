from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, suppress
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from uuid import uuid4

from snekbox.snekio.filesystem import UnmountFlags, mount, unmount


class LibMountTests(TestCase):
    temp_dir: TemporaryDirectory

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = TemporaryDirectory(prefix="snekbox_tests")

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    @contextmanager
    def get_mount(self):
        """Yield a valid mount point and unmount after context."""
        path = Path(self.temp_dir.name, str(uuid4()))
        path.mkdir()
        try:
            mount(source="", target=path, fs="tmpfs")
            yield path
        finally:
            with suppress(OSError):
                unmount(path)

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
                dict(source="", target=self.temp_dir.name, fs="tmpfs", invalid_opt="?"),
                OSError,
                "Invalid argument",
            ),
        ]
        for case, err, msg in cases:
            with self.subTest(case=case):
                with self.assertRaises(err) as cm:
                    mount(**case)
                self.assertIn(msg, str(cm.exception))

    def test_mount_duplicate(self):
        """Test attempted mount after mounted."""
        path = Path(self.temp_dir.name, str(uuid4()))
        path.mkdir()
        try:
            mount(source="", target=path, fs="tmpfs")
            with self.assertRaises(OSError) as cm:
                mount(source="", target=path, fs="tmpfs")
            self.assertIn("already a mount point", str(cm.exception))
        finally:
            unmount(target=path)

    def test_unmount_flags(self):
        """Test unmount flags."""
        flags = [
            UnmountFlags.MNT_FORCE,
            UnmountFlags.MNT_DETACH,
            UnmountFlags.UMOUNT_NOFOLLOW,
        ]
        for flag in flags:
            with self.subTest(flag=flag), self.get_mount() as path:
                self.assertTrue(path.is_mount())
                unmount(path, flag)
                self.assertFalse(path.is_mount())

    def test_unmount_flags_expire(self):
        """Test unmount MNT_EXPIRE behavior."""
        with self.get_mount() as path:
            with self.assertRaises(BlockingIOError):
                unmount(path, UnmountFlags.MNT_EXPIRE)

    def test_unmount_errors(self):
        """Test invalid unmount errors."""
        cases = [
            (dict(target="not/exist"), OSError, "is not a mount point"),
            (dict(target=Path("not/exist")), OSError, "is not a mount point"),
        ]
        for case, err, msg in cases:
            with self.subTest(case=case):
                with self.assertRaises(err) as cm:
                    unmount(**case)
                self.assertIn(msg, str(cm.exception))

    def test_unmount_invalid_args(self):
        """Test invalid unmount invalid flag."""
        with self.get_mount() as path:
            with self.assertRaises(OSError) as cm:
                unmount(path, 251)
            self.assertIn("Invalid argument", str(cm.exception))

    def test_threading(self):
        """Test concurrent mounting works in multi-thread environments."""
        paths = [Path(self.temp_dir.name, str(uuid4())) for _ in range(16)]

        for path in paths:
            path.mkdir()
            self.assertFalse(path.is_mount())

        try:
            with ThreadPoolExecutor() as pool:
                res = list(
                    pool.map(
                        mount,
                        [""] * len(paths),
                        paths,
                        ["tmpfs"] * len(paths),
                    )
                )
                self.assertEqual(len(res), len(paths))

                for path in paths:
                    with self.subTest(path=path):
                        self.assertTrue(path.is_mount())

                unmounts = list(pool.map(unmount, paths))
                self.assertEqual(len(unmounts), len(paths))

                for path in paths:
                    with self.subTest(path=path):
                        self.assertFalse(path.is_mount())
        finally:
            with suppress(OSError):
                for path in paths:
                    unmount(path)
