from textwrap import dedent

from tests.nsjail import NsJailTestCase

from snekbox.nsjail import MEM_MAX


class UnixNsJailTests(NsJailTestCase):
    def test_echo_returns_0(self):
        result = self.nsjail.unix("echo test")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "test\n")
        self.assertEqual(result.stderr, None)

    def test_timeout_returns_137(self):
        cmd = dedent("""
            sleep 10
        """).strip()

        with self.assertLogs(self.logger) as log:
            result = self.nsjail.unix(cmd)

        self.assertEqual(result.returncode, 137)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, None)
        self.assertIn("run time >= time limit", "\n".join(log.output))

    def test_no_alloc_over_mem_limit(self):
        cmd = dedent(f"""
            dd if=/dev/zero bs={MEM_MAX} count=1 | wc -c
        """).strip()

        result = self.nsjail.unix(cmd)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "0\n")
        self.assertEqual(result.stderr, None)

    def test_pid_limit(self):
        # fixme: hardcoded pid limit
        cmd = dedent("""
            for i in {0..10}; do
                sleep 2 &
            done
        """)

        result = self.nsjail.unix(cmd)
        self.assertEqual(result.returncode, 254)
        self.assertIn("Resource temporarily unavailable", result.stdout)
        self.assertEqual(result.stderr, None)

    def test_mtab_not_available(self):
        cmd = dedent("""
            mount
        """)

        result = self.nsjail.unix(cmd)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "mount: failed to read mtab: No such file or directory\n")
        self.assertEqual(result.stderr, None)

    def test_readonly_filesystem(self):
        for path in ("/", "/etc", "/lib", "/lib64", "/snekbox", "/usr"):
            with self.subTest(path=path):
                cmd = dedent(f"""
                    touch {path}/test
                """)

                result = self.nsjail.unix(cmd)
                self.assertEqual(result.returncode, 1)
                self.assertTrue(
                    ("Read-only file system" in result.stdout)
                    or ("No such file or directory" in result.stdout)
                )
                self.assertEqual(result.stderr, None)

    def test_cannot_remount_rootfs(self):
        cmd = dedent("""
            mount / /
        """)

        result = self.nsjail.unix(cmd)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "mount: only root can do that\n")
        self.assertEqual(result.stderr, None)

    def test_fail_gracefully_when_linuxfs_not_setup(self):
        self.nsjail.shell_binary = "/nonexistent/path"
        cmd = dedent("""
            whoami
        """)

        result = self.nsjail.unix(cmd)
        self.assertEqual(result.returncode, None)
        self.assertEqual(result.stdout, "LinuxFS not set up")
        self.assertEqual(result.stderr, None)
