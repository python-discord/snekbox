import io
import logging
import shutil
import sys
import tempfile
import unittest
import unittest.mock
from itertools import product
from pathlib import Path
from textwrap import dedent

from snekbox.nsjail import NsJail
from snekbox.snekio import FileAttachment
from snekbox.snekio.filesystem import Size


class NsJailTests(unittest.TestCase):
    def setUp(self):
        super().setUp()

        # Specify lower limits for unit tests to complete within time limits
        self.nsjail = NsJail(memfs_instance_size=2 * Size.MiB)
        self.logger = logging.getLogger("snekbox.nsjail")
        self.logger.setLevel(logging.WARNING)

        # Hard-coded because it's non-trivial to parse the mount options.
        self.shm_mount_size = 40 * Size.MiB

    def eval_code(self, code: str):
        return self.nsjail.python3(["-c", code])

    def eval_file(self, code: str, name: str = "test.py", **kwargs):
        file = FileAttachment(name, code.encode())
        return self.nsjail.python3([name], [file], **kwargs)

    def test_print_returns_0(self):
        for fn in (self.eval_code, self.eval_file):
            with self.subTest(fn.__name__):
                result = fn("print('test')")
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "test\n")
                self.assertEqual(result.stderr, None)

    def test_timeout_returns_137(self):
        code = "while True: pass"

        with self.assertLogs(self.logger) as log:
            result = self.eval_file(code)

        self.assertEqual(result.returncode, 137)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, None)
        self.assertIn("run time >= time limit", "\n".join(log.output))

    def test_memory_returns_137(self):
        # Add a kilobyte just to be safe.
        code = f"x = ' ' * {self.nsjail.config.cgroup_mem_max + 1000}"

        result = self.eval_file(code)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.returncode, 137)
        self.assertEqual(result.stderr, None)

    def test_multi_files(self):
        files = [
            FileAttachment("main.py", "import lib; print(lib.x)".encode()),
            FileAttachment("lib.py", "x = 'hello'".encode()),
        ]

        result = self.nsjail.python3(["main.py"], files)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "hello\n")
        self.assertEqual(result.stderr, None)

    def test_subprocess_resource_unavailable(self):
        max_pids = self.nsjail.config.cgroup_pids_max
        code = dedent(
            f"""
            import subprocess

            # Should fail at n (max PIDs) since the caller python process counts as well
            for _ in range({max_pids}):
                print(subprocess.Popen(
                    [
                        '/lang/python/default/bin/python',
                        '-c',
                        'import time; time.sleep(1)'
                    ],
                ).pid)
            """
        ).strip()

        result = self.eval_file(code)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Resource temporarily unavailable", result.stdout)
        # Expect n-1 processes to be opened by the presence of string like "2\n3\n4\n"
        expected = "\n".join(map(str, range(2, max_pids + 1)))
        self.assertIn(expected, result.stdout)
        self.assertEqual(result.stderr, None)

    def test_multiprocess_resource_limits(self):
        code = dedent(
            """
            import time
            from multiprocessing import Process

            def f():
                object = "A" * 40_000_000
                time.sleep(0.5)


            proc_1 = Process(target=f)
            proc_2 = Process(target=f)

            proc_1.start()
            proc_2.start()

            proc_1.join()
            proc_2.join()

            print(proc_1.exitcode, proc_2.exitcode)
            """
        )

        result = self.eval_file(code)

        exit_codes = result.stdout.strip().split()
        self.assertIn("-9", exit_codes)
        self.assertEqual(result.stderr, None)

    def test_multiprocessing_pool(self):
        # Validates that shm is working as expected
        code = dedent(
            """
            from multiprocessing import Pool

            def f(x):
                return x*x

            with Pool(2) as p:
                print(p.map(f, [1, 2, 3]))
        """
        )

        result = self.eval_file(code)

        self.assertEqual(result.stdout, "[1, 4, 9]\n")
        self.assertEqual(result.returncode, 0)

    def test_read_only_file_system(self):
        for path in ("/", "/etc", "/lib", "/lib64", "/snekbox", "/usr"):
            with self.subTest(path=path):
                code = dedent(
                    f"""
                    with open('{path}/hello', 'w') as f:
                        f.write('world')
                    """
                ).strip()

                result = self.eval_file(code)
                self.assertEqual(result.returncode, 1)
                self.assertIn("Read-only file system", result.stdout)
                self.assertEqual(result.stderr, None)

    def test_write(self):
        code = dedent(
            """
            from pathlib import Path
            with open('test.txt', 'w') as f:
                f.write('hello')
            print(Path('test.txt').read_text())
            """
        ).strip()

        result = self.eval_file(code)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "hello\n")
        self.assertEqual(result.stderr, None)

    def test_write_exceed_space(self):
        code = dedent(
            f"""
            size = {self.nsjail.memfs_instance_size} // 2048
            with open('f.bin', 'wb') as f:
                for i in range(size):
                    f.write(b'1' * 2048)
            """
        ).strip()

        result = self.eval_file(code)
        self.assertEqual(result.returncode, 1)
        self.assertIn("No space left on device", result.stdout)
        self.assertEqual(result.stderr, None)

    def test_write_hidden_exclude(self):
        """Hidden paths should be excluded from output."""
        code = dedent(
            """
            from pathlib import Path

            Path("normal").mkdir()
            Path("normal/a.txt").write_text("a")
            Path("normal/.hidden.txt").write_text("a")
            Path(".hidden").mkdir()
            Path(".hidden/b.txt").write_text("b")
            """
        ).strip()

        result = self.eval_file(code)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(len(result.files), 1)
        self.assertEqual(result.files[0].content, b"a")

    def test_forkbomb_resource_unavailable(self):
        code = dedent(
            """
            import os
            while 1:
                os.fork()
            """
        ).strip()

        result = self.eval_file(code)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Resource temporarily unavailable", result.stdout)
        self.assertEqual(result.stderr, None)

    def test_file_parsing_timeout(self):
        code = dedent(
            """
            import os
            data = "a" * 1024
            size = 32 * 1024 * 1024

            with open("file", "w") as f:
                for _ in range(size // 1024):
                    f.write(data)

            for i in range(100):
                os.symlink("file", f"file{i}")
            """
        ).strip()
        # A value higher than the actual memory needed is used to avoid the limit
        # on total file size being reached before the timeout when reading.
        nsjail = NsJail(memfs_instance_size=128 * Size.MiB, files_timeout=0.1)
        result = nsjail.python3(["-c", code])
        self.assertEqual(result.returncode, None)
        self.assertEqual(
            result.stdout, "TimeoutError: Exceeded time limit while parsing attachments"
        )
        self.assertEqual(result.stderr, None)

    def test_filename_encoding_illegal_chars(self):
        code = dedent(
            r"""
            with open(b"\xC3.txt", "w") as f:
                f.write("test")
            """
        ).strip()
        result = self.eval_file(code)
        self.assertEqual(result.returncode, None)
        self.assertEqual(
            result.stdout, "FileParsingError: invalid bytes in filename while parsing attachments"
        )
        self.assertEqual(result.stderr, None)

    def test_file_parsing_depth_limit(self):
        code = dedent(
            """
            import os

            x = ""
            for _ in range(1000):
                x += "a/"
                os.mkdir(x)

            open(f"{x}test.txt", "w").write("test")
            """
        ).strip()

        nsjail = NsJail(memfs_instance_size=32 * Size.MiB, files_timeout=5)
        result = nsjail.python3(["-c", code])
        self.assertEqual(result.returncode, None)
        self.assertEqual(
            result.stdout,
            "FileParsingError: Exceeded directory depth limit while parsing attachments",
        )
        self.assertEqual(result.stderr, None)

    def test_file_parsing_size_limit_sparse_files(self):
        tmpfs_size = 8 * Size.MiB
        code = dedent(
            f"""
            import os
            with open("test.txt", "w") as f:
                os.truncate(f.fileno(), {tmpfs_size // 2 + 1})

            with open("test2.txt", "w") as f:
                os.truncate(f.fileno(), {tmpfs_size // 2 + 1})
            """
        )
        nsjail = NsJail(memfs_instance_size=tmpfs_size, files_timeout=5)
        result = nsjail.python3(["-c", code])
        self.assertEqual(result.returncode, 0)
        self.assertEqual(len(result.files), 1)

    def test_file_parsing_size_limit_sparse_files_large(self):
        tmpfs_size = 8 * Size.MiB
        code = dedent(
            f"""
            import os
            with open("test.txt", "w") as f:
                # Use a very large value to ensure the test fails if the
                # file is read even if would have been discarded later.
                os.truncate(f.fileno(), {1024 * Size.TiB})
            """
        )
        nsjail = NsJail(memfs_instance_size=tmpfs_size, files_timeout=5)
        result = nsjail.python3(["-c", code])
        self.assertEqual(result.returncode, 0)
        self.assertEqual(len(result.files), 0)

    def test_file_parsing_size_limit_symlinks(self):
        tmpfs_size = 8 * Size.MiB
        code = dedent(
            f"""
            import os
            data = "a" * 1024
            size = {tmpfs_size // 8}

            with open("file", "w") as f:
                for _ in range(size // 1024):
                    f.write(data)

            for i in range(20):
                os.symlink("file", f"file{{i}}")
            """
        )
        nsjail = NsJail(memfs_instance_size=tmpfs_size, files_timeout=5)
        result = nsjail.python3(["-c", code])
        self.assertEqual(result.returncode, 0)
        self.assertEqual(len(result.files), 8)

    def test_file_write_error(self):
        """Test errors during file write."""
        result = self.nsjail.python3(
            [""],
            [
                FileAttachment("dir/test.txt", b"abc"),
                FileAttachment("dir", b"xyz"),
            ],
        )

        self.assertEqual(result.stdout, "IsADirectoryError: Failed to create file 'dir'.")
        self.assertEqual(result.stderr, None)
        self.assertEqual(result.returncode, None)

    def test_sigsegv_returns_139(self):  # In honour of Juan.
        code = dedent(
            """
            import ctypes
            ctypes.string_at(0)
            """
        ).strip()

        result = self.eval_file(code)
        self.assertEqual(result.returncode, 139)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, None)

    def test_null_byte_value_error(self):
        # This error only occurs with `-c` mode
        result = self.eval_code("\0")
        self.assertEqual(result.returncode, None)
        self.assertEqual(result.stdout, "ValueError: embedded null byte")
        self.assertEqual(result.stderr, None)

    def test_print_bad_unicode_encode_error(self):
        result = self.eval_file("print(chr(56550))")
        self.assertEqual(result.returncode, 1)
        self.assertIn("UnicodeEncodeError", result.stdout)
        self.assertEqual(result.stderr, None)

    def test_unicode_env_erase_escape_fails(self):
        result = self.eval_file(
            dedent(
                """
                import os
                import sys
                os.unsetenv('PYTHONIOENCODING')
                os.execl(sys.executable, 'python', '-c', 'print(chr(56550))')
                """
            ).strip()
        )
        self.assertEqual(result.returncode, None)
        self.assertEqual(result.stdout, "UnicodeDecodeError: invalid Unicode in output pipe")
        self.assertEqual(result.stderr, None)

    @unittest.mock.patch("snekbox.nsjail.DEBUG", new=False)
    def test_log_parser(self):
        log_lines = (
            "[D][2019-06-22T20:07:00+0000][16] void foo::bar()():100 This is a debug message.",
            "[I][2019-06-22T20:07:48+0000] pid=20 ([STANDALONE MODE]) "
            "exited with status: 2, (PIDs left: 0)",
            "[W][2019-06-22T20:06:04+0000][14] void cmdline::logParams(nsjconf_t*)():250 "
            "Process will be UID/EUID=0 in the global user namespace, and will have user "
            "root-level access to files",
            "[W][2019-06-22T20:07:00+0000][16] void foo::bar()():100 This is a warning!",
            "[E][2019-06-22T20:07:00+0000][16] bool "
            "cmdline::setupArgv(nsjconf_t*, int, char**, int)():316 No command-line provided",
            "[F][2019-06-22T20:07:00+0000][16] int main(int, char**)():204 "
            "Couldn't parse cmdline options",
            "Invalid Line",
        )

        with self.assertLogs(self.logger, logging.DEBUG) as log:
            self.nsjail._parse_log(log_lines)

        self.assertIn("DEBUG:snekbox.nsjail:This is a debug message.", log.output)
        self.assertIn("ERROR:snekbox.nsjail:Couldn't parse cmdline options", log.output)
        self.assertIn("ERROR:snekbox.nsjail:No command-line provided", log.output)
        self.assertIn("WARNING:snekbox.nsjail:Failed to parse log line 'Invalid Line'", log.output)
        self.assertIn("WARNING:snekbox.nsjail:This is a warning!", log.output)
        self.assertIn(
            "INFO:snekbox.nsjail:pid=20 ([STANDALONE MODE]) exited with status: 2, (PIDs left: 0)",
            log.output,
        )

    def test_tmp_not_mounted(self):
        code = dedent(
            """
            with open('/tmp/test', 'wb') as file:
                file.write(bytes([255]))
        """
        ).strip()

        result = self.eval_file(code)
        self.assertEqual(result.returncode, 1)
        self.assertIn("No such file or directory", result.stdout)
        self.assertEqual(result.stderr, None)

    def test_multiprocessing_shared_memory(self):
        cases = (
            (self.shm_mount_size, self.shm_mount_size, 0),
            # Even if the shared memory object is larger than the mount,
            # writing data within the size of the mount should succeed.
            (self.shm_mount_size + 1, self.shm_mount_size, 0),
            (self.shm_mount_size + 1, self.shm_mount_size + 1, 135),
        )

        for shm_size, buffer_size, return_code in cases:
            with self.subTest(shm_size=shm_size, buffer_size=buffer_size):
                # Need enough memory for buffer and bytearray plus some overhead.
                mem_max = (buffer_size * 2) + (400 * Size.MiB)
                code = dedent(
                    f"""
                    from multiprocessing.shared_memory import SharedMemory

                    shm = SharedMemory(create=True, size={shm_size})
                    shm.buf[:{buffer_size}] = bytearray([1] * {buffer_size})
                """
                ).strip()

                result = self.eval_file(code, nsjail_args=("--cgroup_mem_max", str(mem_max)))

                self.assertEqual(result.returncode, return_code)
                self.assertEqual(result.stdout, "")
                self.assertEqual(result.stderr, None)

    def test_multiprocessing_shared_memory_mmap_limited(self):
        """The mmap call should be OOM trying to map a large & sparse shared memory object."""
        code = dedent(
            f"""
            from multiprocessing.shared_memory import SharedMemory

            SharedMemory(create=True, size={self.nsjail.config.cgroup_mem_max + Size.GiB})
        """
        ).strip()

        result = self.eval_file(code)
        self.assertEqual(result.returncode, 1)
        self.assertIn("[Errno 12] Cannot allocate memory", result.stdout)
        self.assertEqual(result.stderr, None)

    def test_numpy_import(self):
        result = self.eval_file("import numpy")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, None)

    def test_output_order(self):
        stdout_msg = "greetings from stdout!"
        stderr_msg = "hello from stderr!"
        code = dedent(
            f"""
            print({stdout_msg!r})
            raise ValueError({stderr_msg!r})
            """
        ).strip()

        result = self.eval_file(code)
        self.assertLess(
            result.stdout.find(stdout_msg),
            result.stdout.find(stderr_msg),
            msg="stdout does not come before stderr",
        )
        self.assertEqual(result.stderr, None)

    def test_stdout_flood_results_in_graceful_sigterm(self):
        code = "while True: print('abcdefghij')"

        result = self.eval_file(code)
        self.assertEqual(result.returncode, 143)

    def test_large_output_is_truncated(self):
        chunk = "a" * self.nsjail.read_chunk_size
        expected_chunks = self.nsjail.max_output_size // sys.getsizeof(chunk) + 1

        nsjail_subprocess = unittest.mock.MagicMock()

        # Go 10 chunks over to make sure we exceed the limit
        nsjail_subprocess.stdout = io.StringIO((expected_chunks + 10) * chunk)
        nsjail_subprocess.poll.return_value = None

        output = self.nsjail._consume_stdout(nsjail_subprocess)
        self.assertEqual(output, chunk * expected_chunks)

    def test_nsjail_args(self):
        args = ["foo", "bar"]
        result = self.nsjail.python3((), nsjail_args=args)

        end = result.args.index("--")
        self.assertEqual(result.args[end - len(args) : end], args)

    def test_py_args(self):
        cases = [
            # Normal args
            (["-c", "print('hello')"], ["-c", "print('hello')"]),
            # Leading empty strings should be removed
            (["", "-m", "timeit"], ["-m", "timeit"]),
            (["", "", "-m", "timeit"], ["-m", "timeit"]),
            (["", "", "", "-m", "timeit"], ["-m", "timeit"]),
            # Non-leading empty strings should be preserved
            (["-m", "timeit", ""], ["-m", "timeit", ""]),
        ]

        for args, expected in cases:
            with self.subTest(args=args):
                result = self.nsjail.python3(py_args=args)
                idx = result.args.index(self.nsjail.config.exec_bin.path)
                self.assertEqual(result.args[idx + 1 :], expected)
                self.assertEqual(result.returncode, 0)


class NsJailArgsTests(unittest.TestCase):
    def setUp(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addClassCleanup(self._temp_dir.cleanup)

        self.nsjail_path = shutil.copy2("/usr/sbin/nsjail", self._temp_dir.name)
        self.config_path = shutil.copy2("./config/snekbox.cfg", self._temp_dir.name)
        self.max_output_size = 1_234_567
        self.read_chunk_size = 12_345

        self.nsjail = NsJail(
            self.nsjail_path, self.config_path, self.max_output_size, self.read_chunk_size
        )

        logging.getLogger("snekbox.nsjail").setLevel(logging.WARNING)

    def test_nsjail_path(self):
        result = self.nsjail.python3("")

        self.assertEqual(result.args[0], self.nsjail_path)

    def test_config_path(self):
        result = self.nsjail.python3("")

        i = result.args.index("--config") + 1
        self.assertEqual(result.args[i], self.config_path)

    def test_init_args(self):
        self.assertEqual(self.nsjail.nsjail_path, self.nsjail_path)
        self.assertEqual(self.nsjail.config_path, self.config_path)
        self.assertEqual(self.nsjail.max_output_size, self.max_output_size)
        self.assertEqual(self.nsjail.read_chunk_size, self.read_chunk_size)


class NsJailCgroupTests(unittest.TestCase):
    # This should still pass for v2, even if this test isn't relevant.
    def test_cgroupv1(self):
        logging.getLogger("snekbox.nsjail").setLevel(logging.ERROR)
        logging.getLogger("snekbox.limits.swap").setLevel(logging.ERROR)

        config_base = dedent(
            """
            mode: ONCE
            mount {
                src: "/"
                dst: "/"
                is_bind: true
                rw: false
            }
            exec_bin {
                path: "/bin/su"
                arg: ""
            }
            """
        ).strip()

        cases = (
            (
                (
                    "cgroup_mem_max: 52428800",
                    # memory.limit_in_bytes must be set before memory.memsw.limit_in_bytes
                    "cgroup_mem_max: 52428800\ncgroup_mem_memsw_max: 104857600",
                    "cgroup_mem_max: 52428800\ncgroup_mem_swap_max: 52428800",
                ),
                "cgroup_mem_mount: '/sys/fs/cgroup/memory'",
                "cgroup_mem_parent: 'NSJAILTEST1'",
            ),
            (
                ("cgroup_pids_max: 20",),
                "cgroup_pids_mount: '/sys/fs/cgroup/pids'",
                "cgroup_pids_parent: 'NSJAILTEST2'",
            ),
            (
                ("cgroup_net_cls_classid: 1048577",),
                "cgroup_net_cls_mount: '/sys/fs/cgroup/net_cls'",
                "cgroup_net_cls_parent: 'NSJAILTEST3'",
            ),
            (
                ("cgroup_cpu_ms_per_sec: 800",),
                "cgroup_cpu_mount: '/sys/fs/cgroup/cpu'",
                "cgroup_cpu_parent: 'NSJAILTEST4'",
            ),
        )

        # protobuf doesn't parse correctly when NamedTemporaryFile is used directly.
        with tempfile.TemporaryDirectory() as directory:
            for values, mount, parent in cases:
                for lines in product(values, (mount, ""), (parent, "")):
                    with self.subTest(config=lines):
                        config_path = str(Path(directory, "config.cfg"))
                        with open(config_path, "w", encoding="utf8") as f:
                            f.write("\n".join(lines + (config_base,)))

                        nsjail = NsJail(config_path=config_path)

                        result = nsjail.python3("")

                        self.assertNotEqual(result.returncode, 255)
