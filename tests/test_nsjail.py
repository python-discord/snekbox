import io
import logging
import sys
import unittest
import unittest.mock
from textwrap import dedent

from snekbox.nsjail import NsJail, OUTPUT_MAX, READ_CHUNK_SIZE


class NsJailTests(unittest.TestCase):
    def setUp(self):
        super().setUp()

        self.nsjail = NsJail()
        self.logger = logging.getLogger("snekbox.nsjail")
        self.logger.setLevel(logging.WARNING)

    def test_print_returns_0(self):
        result = self.nsjail.python3("print('test')")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "test\n")
        self.assertEqual(result.stderr, None)

    def test_timeout_returns_137(self):
        code = dedent("""
            while True:
                pass
        """).strip()

        with self.assertLogs(self.logger) as log:
            result = self.nsjail.python3(code)

        self.assertEqual(result.returncode, 137)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, None)
        self.assertIn("run time >= time limit", "\n".join(log.output))

    def test_memory_returns_137(self):
        # Add a kilobyte just to be safe.
        code = dedent(f"""
            x = ' ' * {self.nsjail.config.cgroup_mem_max + 1000}
        """).strip()

        result = self.nsjail.python3(code)
        self.assertEqual(result.returncode, 137)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, None)

    def test_subprocess_resource_unavailable(self):
        code = dedent("""
            import subprocess

            # Max PIDs is 5.
            for _ in range(6):
                print(subprocess.Popen(
                    [
                        '/usr/local/bin/python3',
                        '-c',
                        'import time; time.sleep(1)'
                    ],
                ).pid)
        """).strip()

        result = self.nsjail.python3(code)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Resource temporarily unavailable", result.stdout)
        self.assertEqual(result.stderr, None)

    def test_multiprocess_resource_limits(self):
        code = dedent("""
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
        """)

        result = self.nsjail.python3(code)

        exit_codes = result.stdout.strip().split()
        self.assertIn("-9", exit_codes)
        self.assertEqual(result.stderr, None)

    def test_read_only_file_system(self):
        for path in ("/", "/etc", "/lib", "/lib64", "/snekbox", "/usr"):
            with self.subTest(path=path):
                code = dedent(f"""
                    with open('{path}/hello', 'w') as f:
                        f.write('world')
                """).strip()

                result = self.nsjail.python3(code)
                self.assertEqual(result.returncode, 1)
                self.assertIn("Read-only file system", result.stdout)
                self.assertEqual(result.stderr, None)

    def test_forkbomb_resource_unavailable(self):
        code = dedent("""
            import os
            while 1:
                os.fork()
        """).strip()

        result = self.nsjail.python3(code)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Resource temporarily unavailable", result.stdout)
        self.assertEqual(result.stderr, None)

    def test_sigsegv_returns_139(self):  # In honour of Juan.
        code = dedent("""
            import ctypes
            ctypes.string_at(0)
        """).strip()

        result = self.nsjail.python3(code)
        self.assertEqual(result.returncode, 139)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, None)

    def test_null_byte_value_error(self):
        result = self.nsjail.python3("\0")
        self.assertEqual(result.returncode, None)
        self.assertEqual(result.stdout, "ValueError: embedded null byte")
        self.assertEqual(result.stderr, None)

    def test_print_bad_unicode_encode_error(self):
        result = self.nsjail.python3("print(chr(56550))")
        self.assertEqual(result.returncode, 1)
        self.assertIn("UnicodeEncodeError", result.stdout)
        self.assertEqual(result.stderr, None)

    def test_unicode_env_erase_escape_fails(self):
        result = self.nsjail.python3(dedent("""
            import os
            import sys
            os.unsetenv('PYTHONIOENCODING')
            os.execl(sys.executable, 'python', '-c', 'print(chr(56550))')
        """).strip())
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
            "Invalid Line"
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
            log.output
        )

    def test_shm_and_tmp_not_mounted(self):
        for path in ("/dev/shm", "/run/shm", "/tmp"):
            with self.subTest(path=path):
                code = dedent(f"""
                    with open('{path}/test', 'wb') as file:
                        file.write(bytes([255]))
                """).strip()

                result = self.nsjail.python3(code)
                self.assertEqual(result.returncode, 1)
                self.assertIn("No such file or directory", result.stdout)
                self.assertEqual(result.stderr, None)

    def test_multiprocessing_shared_memory_disabled(self):
        code = dedent("""
            from multiprocessing.shared_memory import SharedMemory
            try:
                SharedMemory('test', create=True, size=16)
            except FileExistsError:
                pass
        """).strip()

        result = self.nsjail.python3(code)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Function not implemented", result.stdout)
        self.assertEqual(result.stderr, None)

    def test_numpy_import(self):
        result = self.nsjail.python3("import numpy")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, None)

    def test_output_order(self):
        stdout_msg = "greetings from stdout!"
        stderr_msg = "hello from stderr!"
        code = dedent(f"""
            print({stdout_msg!r})
            raise ValueError({stderr_msg!r})
        """).strip()

        result = self.nsjail.python3(code)
        self.assertLess(
            result.stdout.find(stdout_msg),
            result.stdout.find(stderr_msg),
            msg="stdout does not come before stderr"
        )
        self.assertEqual(result.stderr, None)

    def test_stdout_flood_results_in_graceful_sigterm(self):
        stdout_flood = dedent("""
            while True:
                print('abcdefghij')
        """).strip()

        result = self.nsjail.python3(stdout_flood)
        self.assertEqual(result.returncode, 143)

    def test_large_output_is_truncated(self):
        chunk = "a" * READ_CHUNK_SIZE
        expected_chunks = OUTPUT_MAX // sys.getsizeof(chunk) + 1

        nsjail_subprocess = unittest.mock.MagicMock()

        # Go 10 chunks over to make sure we exceed the limit
        nsjail_subprocess.stdout = io.StringIO((expected_chunks + 10) * chunk)
        nsjail_subprocess.poll.return_value = None

        output = self.nsjail._consume_stdout(nsjail_subprocess)
        self.assertEqual(output, chunk * expected_chunks)

    def test_nsjail_args(self):
        args = ("foo", "bar")
        result = self.nsjail.python3("", nsjail_args=args)

        end = result.args.index("--")
        self.assertEqual(result.args[end - len(args):end], args)

    def test_py_args(self):
        args = ("-m", "timeit")
        result = self.nsjail.python3("", py_args=args)

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.args[-3:-1], args)
