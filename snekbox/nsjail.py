import logging
import os
import re
import subprocess
import sys
import textwrap
from subprocess import CompletedProcess
from tempfile import NamedTemporaryFile
from typing import Iterable

from google.protobuf import text_format

from snekbox import DEBUG, utils
from snekbox.config_pb2 import NsJailConfig

log = logging.getLogger(__name__)

# [level][timestamp][PID]? function_signature:line_no? message
LOG_PATTERN = re.compile(
    r"\[(?P<level>(I)|[DWEF])\]\[.+?\](?(2)|(?P<func>\[\d+\] .+?:\d+ )) ?(?P<msg>.+)"
)
LOG_BLACKLIST = ("Process will be ",)

NSJAIL_PATH = os.getenv("NSJAIL_PATH", "/usr/sbin/nsjail")
NSJAIL_CFG = os.getenv("NSJAIL_CFG", "./config/snekbox.cfg")

# Limit of stdout bytes we consume before terminating nsjail
OUTPUT_MAX = 1_000_000  # 1 MB
READ_CHUNK_SIZE = 10_000  # chars


class NsJail:
    """
    Core Snekbox functionality, providing safe execution of Python code.

    See config/snekbox.cfg for the default NsJail configuration.
    """

    def __init__(self, nsjail_binary: str = NSJAIL_PATH):
        self.nsjail_binary = nsjail_binary
        self.config = self._read_config()
        self.cgroup_version = utils.cgroup.init(self.config)
        self.ignore_swap_limits = utils.swap.should_ignore_limit(self.config, self.cgroup_version)

        log.info(f"Assuming cgroup version {self.cgroup_version}.")

    @staticmethod
    def _read_config() -> NsJailConfig:
        """Read the NsJail config at `NSJAIL_CFG` and return a protobuf Message object."""
        config = NsJailConfig()

        try:
            with open(NSJAIL_CFG, encoding="utf-8") as f:
                config_text = f.read()
        except FileNotFoundError:
            log.fatal(f"The NsJail config at {NSJAIL_CFG!r} could not be found.")
            sys.exit(1)
        except OSError as e:
            log.fatal(f"The NsJail config at {NSJAIL_CFG!r} could not be read.", exc_info=e)
            sys.exit(1)

        try:
            text_format.Parse(config_text, config)
        except text_format.ParseError as e:
            log.fatal(f"The NsJail config at {NSJAIL_CFG!r} could not be parsed.", exc_info=e)
            sys.exit(1)

        return config

    @staticmethod
    def _parse_log(log_lines: Iterable[str]) -> None:
        """Parse and log NsJail's log messages."""
        for line in log_lines:
            match = LOG_PATTERN.fullmatch(line)
            if match is None:
                log.warning(f"Failed to parse log line '{line}'")
                continue

            msg = match["msg"]
            if not DEBUG and any(msg.startswith(s) for s in LOG_BLACKLIST):
                # Skip blacklisted messages if not debugging.
                continue

            if DEBUG and match["func"]:
                # Prepend PID, function signature, and line number if debugging.
                msg = f"{match['func']}{msg}"

            if match["level"] == "D":
                log.debug(msg)
            elif match["level"] == "I":
                if DEBUG or msg.startswith("pid="):
                    # Skip messages unrelated to process exit if not debugging.
                    log.info(msg)
            elif match["level"] == "W":
                log.warning(msg)
            else:
                # Treat fatal as error.
                log.error(msg)

    @staticmethod
    def _consume_stdout(nsjail: subprocess.Popen) -> str:
        """
        Consume STDOUT, stopping when the output limit is reached or NsJail has exited.

        The aim of this function is to limit the size of the output received from
        NsJail to prevent container from claiming too much memory. If the output
        received from STDOUT goes over the OUTPUT_MAX limit, the NsJail subprocess
        is asked to terminate with a SIGKILL.

        Once the subprocess has exited, either naturally or because it was terminated,
        we return the output as a single string.
        """
        output_size = 0
        output = []

        # Context manager will wait for process to terminate and close file descriptors.
        with nsjail:
            # We'll consume STDOUT as long as the NsJail subprocess is running.
            while nsjail.poll() is None:
                chars = nsjail.stdout.read(READ_CHUNK_SIZE)
                output_size += sys.getsizeof(chars)
                output.append(chars)

                if output_size > OUTPUT_MAX:
                    # Terminate the NsJail subprocess with SIGTERM.
                    # This in turn reaps and kills children with SIGKILL.
                    log.info("Output exceeded the output limit, sending SIGTERM to NsJail.")
                    nsjail.terminate()
                    break

        return "".join(output)

    def python3(
        self,
        code: str,
        *,
        nsjail_args: Iterable[str] = (),
        py_args: Iterable[str] = ("-c",)
    ) -> CompletedProcess:
        """
        Execute Python 3 code in an isolated environment and return the completed process.

        The `nsjail_args` passed will be used to override the values in the NsJail config.
        These arguments are only options for NsJail; they do not affect Python's arguments.

        `py_args` are arguments to pass to the Python subprocess before the code,
        which is the last argument. By default, it's "-c", which executes the code given.
        """
        if self.cgroup_version == 2:
            nsjail_args = ("--use_cgroupv2", *nsjail_args)

        if self.ignore_swap_limits:
            nsjail_args = (
                "--cgroup_mem_memsw_max", "0", "--cgroup_mem_swap_max", "-1", *nsjail_args
            )

        with NamedTemporaryFile() as nsj_log:
            args = (
                self.nsjail_binary,
                "--config", NSJAIL_CFG,
                "--log", nsj_log.name,
                *nsjail_args,
                "--",
                self.config.exec_bin.path, *self.config.exec_bin.arg, *py_args, code
            )

            msg = "Executing code..."
            if DEBUG:
                msg = f"{msg[:-3]}:\n{textwrap.indent(code, '    ')}\nWith the arguments {args}."
            log.info(msg)

            try:
                nsjail = subprocess.Popen(
                    args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )
            except ValueError:
                return CompletedProcess(args, None, "ValueError: embedded null byte", None)

            try:
                output = self._consume_stdout(nsjail)
            except UnicodeDecodeError:
                return CompletedProcess(
                    args,
                    None,
                    "UnicodeDecodeError: invalid Unicode in output pipe",
                    None,
                )

            # When you send signal `N` to a subprocess to terminate it using Popen, it
            # will return `-N` as its exit code. As we normally get `N + 128` back, we
            # convert negative exit codes to the `N + 128` form.
            returncode = -nsjail.returncode + 128 if nsjail.returncode < 0 else nsjail.returncode

            log_lines = nsj_log.read().decode("utf-8").splitlines()
            if not log_lines and returncode == 255:
                # NsJail probably failed to parse arguments so log output will still be in stdout
                log_lines = output.splitlines()

            self._parse_log(log_lines)

        log.info(f"nsjail return code: {returncode}")

        return CompletedProcess(args, returncode, output, None)
