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
MEM_MAX = 52428800

# python3-specifc configuration
NSJAIL_CFG_SNEKBOX = os.getenv("NSJAIL_CFG_SNEKBOX", "./config/snekbox.cfg")

# unix-specific configuration
SHELL_PATH = os.getenv("SHELL_PATH", "/bin/bash")
LINUXFS_DIR_PATH = os.getenv("LINUXFS_DIR_PATH", "/snekbox/linuxfs")
NSJAIL_CFG_UNIXCMD = os.getenv("NSJAIL_CFG_UNIXCMD", "./config/unixcmd.cfg")


class NsJail:
    """
    Core Snekbox functionality, providing safe execution of Python code.

    See config/snekbox.cfg for the default NsJail configuration.
    """

    def __init__(
        self,
        nsjail_binary: str = NSJAIL_PATH,
        python_binary: str = sys.executable,
        shell_binary: str = SHELL_PATH
    ):
        self.nsjail_binary = nsjail_binary
        self.python_binary = python_binary
        self.shell_binary = shell_binary

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

    def _jail_execute(self, nsjail_cfg: str, exec_args: tuple) -> CompletedProcess:
        """Execute a process in an isolated environment and return the completed process."""
        with NamedTemporaryFile() as nsj_log:
            nsjail_args = (
                self.nsjail_binary,
                "--config", nsjail_cfg,
                "--log", nsj_log.name,
                f"--cgroup_mem_max={MEM_MAX}",
                "--cgroup_mem_mount", str(CGROUP_MEMORY_PARENT.parent),
                "--cgroup_mem_parent", CGROUP_MEMORY_PARENT.name,
                "--cgroup_pids_mount", str(CGROUP_PIDS_PARENT.parent),
                "--cgroup_pids_parent", CGROUP_PIDS_PARENT.name,
                "--"
            )

            msg = "Executing code..."
            if DEBUG:
                msg = f"{msg[:-3]}:\n{textwrap.indent(exec_args[-1], '    ')}"
            log.info(msg)

            args = nsjail_args + exec_args
            try:
                result = subprocess.run(
                    args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )
            except ValueError:
                return CompletedProcess(args, None, "ValueError: embedded null byte", None)

            log_lines = nsj_log.read().decode("utf-8").splitlines()
            if not log_lines and result.returncode == 255:
                # NsJail probably failed to parse arguments so log output will still be in stdout
                log_lines = result.stdout.splitlines()

            self._parse_log(log_lines)

        return result

    def python3(self, code: str) -> CompletedProcess:
        """Execute Python 3 code in an isolated environment and return the completed process."""
        args = (self.python_binary, "-Iqu", "-c", code)

        return self._jail_execute(NSJAIL_CFG_SNEKBOX, args)

    def unix(self, cmd: str) -> CompletedProcess:
        """Execute a unix command in an isolated system shell and return the completed process."""
        if not Path(f"{LINUXFS_DIR_PATH}/{self.shell_binary}").is_file():
            log.warning("Attempted to run Unix commands with no LinuxFS set up")
            return CompletedProcess((), None, "LinuxFS not set up", None)

        args = (self.shell_binary, "-c", cmd)

        return self._jail_execute(NSJAIL_CFG_UNIXCMD, args)
