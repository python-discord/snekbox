import logging
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path
from subprocess import CompletedProcess
from tempfile import NamedTemporaryFile
from typing import Iterable

from snekbox import DEBUG

log = logging.getLogger(__name__)

# [level][timestamp][PID]? function_signature:line_no? message
LOG_PATTERN = re.compile(
    r"\[(?P<level>(I)|[DWEF])\]\[.+?\](?(2)|(?P<func>\[\d+\] .+?:\d+ )) ?(?P<msg>.+)"
)
LOG_BLACKLIST = ("Process will be ",)

# Explicitly define constants for NsJail's default values.
CGROUP_PIDS_PARENT = Path("/sys/fs/cgroup/pids/NSJAIL")
CGROUP_MEMORY_PARENT = Path("/sys/fs/cgroup/memory/NSJAIL")

NSJAIL_PATH = os.getenv("NSJAIL_PATH", "/usr/sbin/nsjail")
NSJAIL_CFG = os.getenv("NSJAIL_CFG", "./config/snekbox.cfg")
MEM_MAX = 52428800

# Limit of stdout bytes we consume before terminating nsjail
OUTPUT_MAX = 1_000_000  # 1 MB
READ_CHUNK_SIZE = 10_000  # chars


class NsJail:
    """
    Core Snekbox functionality, providing safe execution of Python code.

    See config/snekbox.cfg for the default NsJail configuration.
    """

    def __init__(self, nsjail_binary: str = NSJAIL_PATH, python_binary: str = sys.executable):
        self.nsjail_binary = nsjail_binary
        self.python_binary = python_binary

        self._create_parent_cgroups()

    @staticmethod
    def _create_parent_cgroups(
        pids: Path = CGROUP_PIDS_PARENT,
        mem: Path = CGROUP_MEMORY_PARENT
    ) -> None:
        """
        Create the PIDs and memory cgroups which NsJail will use as its parent cgroups.

        NsJail doesn't do this automatically because it requires privileges NsJail usually doesn't
        have.

        Disables memory swapping.
        """
        pids.mkdir(parents=True, exist_ok=True)
        mem.mkdir(parents=True, exist_ok=True)

        # Swap limit cannot be set to a value lower than memory.limit_in_bytes.
        # Therefore, this must be set first.
        (mem / "memory.limit_in_bytes").write_text(str(MEM_MAX), encoding="utf-8")

        try:
            # Swap limit is specified as the sum of the memory and swap limits.
            (mem / "memory.memsw.limit_in_bytes").write_text(str(MEM_MAX), encoding="utf-8")
        except PermissionError:
            log.warning(
                "Failed to set the memory swap limit for the cgroup. "
                "This is probably because CONFIG_MEMCG_SWAP or CONFIG_MEMCG_SWAP_ENABLED is unset. "
                "Please ensure swap memory is disabled on the system."
            )

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

        # We'll consume STDOUT as long as the NsJail subprocess is running.
        while nsjail.poll() is None:
            chars = nsjail.stdout.read(READ_CHUNK_SIZE)
            output_size += sys.getsizeof(chars)
            output.append(chars)

            if output_size > OUTPUT_MAX:
                # Terminate the NsJail subprocess with SIGKILL.
                log.info("Output exceeded the output limit, sending SIGKILL to NsJail.")
                nsjail.kill()
                break

        # Ensure that we wait for the NsJail subprocess to terminate.
        nsjail.wait()

        return "".join(output)

    def python3(self, code: str) -> CompletedProcess:
        """Execute Python 3 code in an isolated environment and return the completed process."""
        with NamedTemporaryFile() as nsj_log:
            args = (
                self.nsjail_binary,
                "--config", NSJAIL_CFG,
                "--log", nsj_log.name,
                f"--cgroup_mem_max={MEM_MAX}",
                "--cgroup_mem_mount", str(CGROUP_MEMORY_PARENT.parent),
                "--cgroup_mem_parent", CGROUP_MEMORY_PARENT.name,
                "--cgroup_pids_max=1",
                "--cgroup_pids_mount", str(CGROUP_PIDS_PARENT.parent),
                "--cgroup_pids_parent", CGROUP_PIDS_PARENT.name,
                "--",
                self.python_binary, "-Squ", "-c", code
            )

            msg = "Executing code..."
            if DEBUG:
                msg = f"{msg[:-3]}:\n{textwrap.indent(code, '    ')}"
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

            output = self._consume_stdout(nsjail)

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
