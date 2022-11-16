import logging
import re
import subprocess
import sys
import textwrap
from tempfile import NamedTemporaryFile
from typing import Iterable

from google.protobuf import text_format

# noinspection PyProtectedMember
from snekbox import DEBUG, utils
from snekbox.config_pb2 import NsJailConfig
from snekbox.memfs import MemoryTempDir

__all__ = ("NsJail",)

from snekbox.process import EvalResult
from snekbox.snekio import AttachmentError

log = logging.getLogger(__name__)

# [level][timestamp][PID]? function_signature:line_no? message
LOG_PATTERN = re.compile(
    r"\[(?P<level>(I)|[DWEF])\]\[.+?\](?(2)|(?P<func>\[\d+\] .+?:\d+ )) ?(?P<msg>.+)"
)


class NsJail:
    """
    Core Snekbox functionality, providing safe execution of Python code.

    See config/snekbox.cfg for the default NsJail configuration.
    """

    def __init__(
        self,
        nsjail_path: str = "/usr/sbin/nsjail",
        config_path: str = "./config/snekbox.cfg",
        max_output_size: int = 1_000_000,
        read_chunk_size: int = 10_000,
    ):
        self.nsjail_path = nsjail_path
        self.config_path = config_path
        self.max_output_size = max_output_size
        self.read_chunk_size = read_chunk_size

        self.config = self._read_config(config_path)
        self.cgroup_version = utils.cgroup.init(self.config)
        self.ignore_swap_limits = utils.swap.should_ignore_limit(self.config, self.cgroup_version)

        log.info(f"Assuming cgroup version {self.cgroup_version}.")

    @staticmethod
    def _read_config(config_path: str) -> NsJailConfig:
        """Read the NsJail config at `config_path` and return a protobuf Message object."""
        config = NsJailConfig()

        try:
            with open(config_path, encoding="utf-8") as f:
                config_text = f.read()
        except FileNotFoundError:
            log.fatal(f"The NsJail config at {config_path!r} could not be found.")
            sys.exit(1)
        except OSError as e:
            log.fatal(f"The NsJail config at {config_path!r} could not be read.", exc_info=e)
            sys.exit(1)

        try:
            text_format.Parse(config_text, config)
        except text_format.ParseError as e:
            log.fatal(f"The NsJail config at {config_path!r} could not be parsed.", exc_info=e)
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

    def _consume_stdout(self, nsjail: subprocess.Popen) -> str:
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
                chars = nsjail.stdout.read(self.read_chunk_size)
                output_size += sys.getsizeof(chars)
                output.append(chars)

                if output_size > self.max_output_size:
                    # Terminate the NsJail subprocess with SIGTERM.
                    # This in turn reaps and kills children with SIGKILL.
                    log.info("Output exceeded the output limit, sending SIGTERM to NsJail.")
                    nsjail.terminate()
                    break

        return "".join(output)

    def python3(
        self, code: str, *, nsjail_args: Iterable[str] = (), py_args: Iterable[str] = ("",)
    ) -> EvalResult:
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
                "--cgroup_mem_memsw_max",
                "0",
                "--cgroup_mem_swap_max",
                "-1",
                *nsjail_args,
            )

        with NamedTemporaryFile() as nsj_log, MemoryTempDir() as temp_dir:
            # Write the code to a python file in the temp directory.
            with temp_dir.allow_write():
                code_path = temp_dir.home / "main.py"
                code_path.write_text(code)
            log.info(f"Created code file at [{code_path!r}].")

            # Add the temp dir to be mounted as cwd
            nsjail_args = (
                "--bindmount",  # Mount temp dir in R/W mode
                f"{temp_dir.home}:home",
                "--cwd",  # Set cwd to temp dir
                "home",
                "--env",  # Set $HOME to temp dir
                "HOME=home",
                *nsjail_args,
            )

            args = (
                self.nsjail_path,
                "--config",
                self.config_path,
                "--log",
                nsj_log.name,
                *nsjail_args,
                "--",
                self.config.exec_bin.path,
                *self.config.exec_bin.arg,
                *[arg for arg in py_args if arg != "-c"],
                "main.py",
            )

            msg = "Executing code..."
            if DEBUG:
                msg = f"{msg[:-3]}:\n{textwrap.indent(code, '    ')}\nWith the arguments {args}."
            log.info(msg)

            try:
                nsjail = subprocess.Popen(
                    args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
                )
            except ValueError:
                return EvalResult(args, None, "ValueError: embedded null byte")

            try:
                output = self._consume_stdout(nsjail)
            except UnicodeDecodeError:
                return EvalResult(args, None, "UnicodeDecodeError: invalid Unicode in output pipe")

            # When you send signal `N` to a subprocess to terminate it using Popen, it
            # will return `-N` as its exit code. As we normally get `N + 128` back, we
            # convert negative exit codes to the `N + 128` form.
            returncode = -nsjail.returncode + 128 if nsjail.returncode < 0 else nsjail.returncode

            # Parse attachments
            try:
                attachments = list(temp_dir.attachments())
                log.info(f"Found {len(attachments)} attachments.")
            except AttachmentError as err:
                log.error(f"Failed to parse attachments: {err}")
                return EvalResult(args, returncode, f"AttachmentError: {err}")

            log_lines = nsj_log.read().decode("utf-8").splitlines()
            if not log_lines and returncode == 255:
                # NsJail probably failed to parse arguments so log output will still be in stdout
                log_lines = output.splitlines()

            self._parse_log(log_lines)

        log.info(f"nsjail return code: {returncode}")

        return EvalResult(args, returncode, output, attachments=attachments)
