import logging
import re
import subprocess
import sys
import textwrap
from pathlib import Path
from tempfile import NamedTemporaryFile

from snekbox import DEBUG

log = logging.getLogger(__name__)

# [level][timestamp][PID]? function_signature:line_no? message
LOG_PATTERN = re.compile(
    r"\[(?P<level>(I)|[WEF])\]\[.+?\](?(2)|(?P<func>\[\d+\] .+?:\d+ )) ?(?P<msg>.+)"
)
LOG_BLACKLIST = ("Process will be ",)

# Explicitly define constants for NsJail's default values.
CGROUP_PIDS_PARENT = Path("/sys/fs/cgroup/pids/NSJAIL")
CGROUP_MEMORY_PARENT = Path("/sys/fs/cgroup/memory/NSJAIL")

ENV = {
    "PATH": (
        "/snekbox/.venv/bin:/usr/local/bin:/usr/local/"
        "sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    ),
    "LANG": "en_US.UTF-8",
    "PYTHON_VERSION": "3.7.3",
    "PYTHON_PIP_VERSION": "19.0.3",
    "PYTHONDONTWRITEBYTECODE": "1",
}


class NsJail:
    """
    Core Snekbox functionality, providing safe execution of Python code.

    NsJail configuration:

    - Root directory is mounted as read-only
    - Time limit of 2 seconds
    - Maximum of 1 PID
    - Maximum memory of 52428800 bytes
    - Loopback interface is down
    - procfs is disabled

    Python configuration:

    - Isolated mode
        - Neither the script's directory nor the user's site packages are in sys.path
        - All PYTHON* environment variables are ignored
    - Import of the site module is disabled
    """

    def __init__(self, nsjail_binary="nsjail", python_binary=sys.executable):
        self.nsjail_binary = nsjail_binary
        self.python_binary = python_binary

        self._create_parent_cgroups()

    @staticmethod
    def _create_parent_cgroups(pids: Path = CGROUP_PIDS_PARENT, mem: Path = CGROUP_MEMORY_PARENT):
        """
        Create the PIDs and memory cgroups which NsJail will use as its parent cgroups.

        NsJail doesn't do this automatically because it requires privileges NsJail usually doesn't
        have.
        """
        pids.mkdir(parents=True, exist_ok=True)
        mem.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _parse_log(log_file):
        """Parse and log NsJail's log messages."""
        for line in log_file.read().decode("UTF-8").splitlines():
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

    def python3(self, code: str) -> subprocess.CompletedProcess:
        """Execute Python 3 code in an isolated environment and return the completed process."""
        with NamedTemporaryFile() as nsj_log:
            args = (
                self.nsjail_binary, "-Mo",
                "--rlimit_as", "700",
                "--chroot", "/",
                "-E", "LANG=en_US.UTF-8",
                "-R/usr", "-R/lib", "-R/lib64",
                "--user", "nobody",
                "--group", "nogroup",
                "--time_limit", "2",
                "--disable_proc",
                "--iface_no_lo",
                "--log", nsj_log.name,
                "--cgroup_mem_max=52428800",
                "--cgroup_mem_mount", str(CGROUP_MEMORY_PARENT.parent),
                "--cgroup_mem_parent", CGROUP_MEMORY_PARENT.name,
                "--cgroup_pids_max=1",
                "--cgroup_pids_mount", str(CGROUP_PIDS_PARENT.parent),
                "--cgroup_pids_parent", CGROUP_PIDS_PARENT.name,
                "--",
                self.python_binary, "-ISq", "-c", code
            )

            msg = "Executing code..."
            if DEBUG:
                msg = f"{msg[:-3]}:\n{textwrap.indent(code, '    ')}"
            log.info(msg)

            try:
                result = subprocess.run(args, capture_output=True, env=ENV, text=True)
            except ValueError:
                return subprocess.CompletedProcess(args, None, "", "ValueError: embedded null byte")

            self._parse_log(nsj_log)

        return result
