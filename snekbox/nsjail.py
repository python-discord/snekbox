import logging
import re
import subprocess
import sys
from collections.abc import Iterable, Sequence
from contextlib import nullcontext
from pathlib import Path
from tempfile import NamedTemporaryFile

from google.protobuf import text_format

from snekbox import DEBUG, limits
from snekbox.config_pb2 import NsJailConfig
from snekbox.limits.timed import time_limit
from snekbox.result import EvalError, EvalResult
from snekbox.snekio import FileAttachment, MemFS
from snekbox.snekio.errors import IllegalPathError
from snekbox.snekio.filesystem import Size
from snekbox.utils.iter import iter_lstrip

__all__ = ("NsJail",)

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
        memfs_instance_size: int = 48 * Size.MiB,
        memfs_home: str = "home",
        memfs_output: str = "home",
        files_limit: int | None = 100,
        files_timeout: float | None = 5,
        files_pattern: str = "**/[!_]*",
    ):
        """
        Initialize NsJail.

        Args:
            nsjail_path: Path to the NsJail binary.
            config_path: Path to the NsJail configuration file.
            max_output_size: Maximum size of the output in bytes.
            read_chunk_size: Size of the read buffer in bytes.
            memfs_instance_size: Size of the tmpfs instance in bytes.
            memfs_home: Name of the mounted home directory.
            memfs_output: Name of the output directory within home,
                can be empty to use home as output.
            files_limit: Maximum number of output files to parse.
            files_timeout: Maximum time in seconds to wait for output files to be read.
            files_pattern: Pattern to match files to attach within the output directory.
        """
        self.nsjail_path = nsjail_path
        self.config_path = config_path
        self.max_output_size = max_output_size
        self.read_chunk_size = read_chunk_size

        self.memfs_instance_size = memfs_instance_size
        self.memfs_home = memfs_home
        self.memfs_output = memfs_output
        self.files_limit = files_limit
        self.files_timeout = files_timeout
        self.files_pattern = files_pattern

        self.config = self._read_config(config_path)
        self.cgroup_version = limits.cgroup.init(self.config)
        self.ignore_swap_limits = limits.swap.should_ignore_limit(self.config, self.cgroup_version)

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
                try:
                    chars = nsjail.stdout.read(self.read_chunk_size)
                except UnicodeDecodeError as e:
                    raise EvalError("UnicodeDecodeError: invalid Unicode in output pipe") from e

                output_size += sys.getsizeof(chars)
                output.append(chars)

                if output_size > self.max_output_size:
                    # Terminate the NsJail subprocess with SIGTERM.
                    # This in turn reaps and kills children with SIGKILL.
                    log.info("Output exceeded the output limit. Sending SIGTERM to NsJail.")
                    nsjail.terminate()
                    break

        return "".join(output)

    def _build_args(
        self, py_args: Iterable[str], nsjail_args: Iterable[str], log_path: str, fs_home: str
    ) -> Sequence[str]:
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

        nsjail_args = (
            # Mount `home` with Read/Write access
            "--bindmount",
            f"{fs_home}:home",
            *nsjail_args,
        )

        return [
            self.nsjail_path,
            "--config",
            self.config_path,
            "--log",
            log_path,
            *nsjail_args,
            "--",
            self.config.exec_bin.path,
            # Filter out empty strings at start of Python args
            # (causes issues with python cli)
            *iter_lstrip(self.config.exec_bin.arg),
            *iter_lstrip(py_args),
        ]

    def _write_files(self, home: Path, files: Iterable[FileAttachment]) -> dict[Path, float]:
        files_written = {}
        for file in files:
            try:
                f_path = file.save_to(home)
                # Allow file to be writable
                f_path.chmod(0o777)
                # Save the written at time to later check if it was modified
                files_written[f_path] = f_path.stat().st_mtime
                log.info(f"Created file at {(home / file.path)!r}.")
            except OSError as e:
                log.info(f"Failed to create file at {(home / file.path)!r}.", exc_info=e)
                raise EvalError(
                    f"{e.__class__.__name__}: Failed to create file '{file.path}'."
                ) from e

        return files_written

    def _parse_attachments(
        self, fs: MemFS, files_written: dict[Path, float]
    ) -> list[FileAttachment]:
        try:
            with time_limit(self.files_timeout) if self.files_timeout else nullcontext():
                attachments = fs.files_list(
                    limit=self.files_limit,
                    pattern=self.files_pattern,
                    preload_dict=True,
                    exclude_files=files_written,
                    timeout=self.files_timeout,
                )

            log.info(f"Found {len(attachments)} files.")
            return attachments
        except RecursionError as e:
            log.info("Recursion error while parsing attachments")
            raise EvalError(
                "FileParsingError: Exceeded directory depth limit while parsing attachments"
            ) from e
        except TimeoutError as e:
            log.info(f"Exceeded time limit while parsing attachments: {e}")
            raise EvalError("TimeoutError: Exceeded time limit while parsing attachments") from e
        except IllegalPathError as e:
            log.info(f"Invalid bytes in filename while parsing attachments: {e}")
            raise EvalError(
                "FileParsingError: invalid bytes in filename while parsing attachments"
            ) from e
        except Exception as e:
            log.exception(f"Unexpected {type(e).__name__} while parse attachments", exc_info=e)
            raise EvalError("FileParsingError: Unknown error while parsing attachments") from e

    def python3(
        self,
        py_args: Iterable[str],
        files: Iterable[FileAttachment] = (),
        nsjail_args: Iterable[str] = (),
    ) -> EvalResult:
        """
        Execute Python 3 code in an isolated environment and return the completed process.

        Args:
            py_args: Arguments to pass to Python.
            files: FileAttachments to write to the sandbox prior to running Python.
            nsjail_args: Overrides for the NsJail configuration.
        """
        with NamedTemporaryFile() as nsj_log, MemFS(
            instance_size=self.memfs_instance_size,
            home=self.memfs_home,
            output=self.memfs_output,
        ) as fs:
            args = self._build_args(py_args, nsjail_args, nsj_log.name, str(fs.home))
            try:
                files_written = self._write_files(fs.home, files)

                msg = "Executing code..."
                if DEBUG:
                    msg = f"{msg[:-3]} with the arguments {args}."
                log.info(msg)

                try:
                    nsjail = subprocess.Popen(
                        args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
                    )
                except ValueError:
                    return EvalResult(args, None, "ValueError: embedded null byte")

                output = self._consume_stdout(nsjail)
                attachments = self._parse_attachments(fs, files_written)
                log_lines = nsj_log.read().decode("utf-8").splitlines()
            except EvalError as e:
                return EvalResult(args, None, str(e))

        # When you send signal `N` to a subprocess to terminate it using Popen, it
        # will return `-N` as its exit code. As we normally get `N + 128` back, we
        # convert negative exit codes to the `N + 128` form.
        return_code = -nsjail.returncode + 128 if nsjail.returncode < 0 else nsjail.returncode

        if not log_lines and return_code == 255:
            # NsJail probably failed to parse arguments so log output will still be in stdout
            log_lines = output.splitlines()

        self._parse_log(log_lines)
        log.info(f"NsJail return code: {return_code}")

        return EvalResult(args, return_code, output, files=attachments)
