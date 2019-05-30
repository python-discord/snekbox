import subprocess
import sys
from pathlib import Path

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

    def python3(self, code: str) -> str:
        """Execute Python 3 code in an isolated environment and return stdout or an error."""
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
            "--cgroup_mem_max=52428800",
            "--cgroup_mem_mount", str(CGROUP_MEMORY_PARENT.parent),
            "--cgroup_mem_parent", CGROUP_MEMORY_PARENT.name,
            "--cgroup_pids_max=1",
            "--cgroup_pids_mount", str(CGROUP_PIDS_PARENT.parent),
            "--cgroup_pids_parent", CGROUP_PIDS_PARENT.name,
            "--quiet", "--",
            self.python_binary, "-ISq", "-c", code
        )

        try:
            proc = subprocess.run(args, capture_output=True, env=ENV, text=True)
        except ValueError:
            return "ValueError: embedded null byte"

        if proc.returncode == 0:
            output = proc.stdout
        elif proc.returncode == 1:
            filtered = (line for line in proc.stderr.split("\n") if not line.startswith("["))
            output = "\n".join(filtered)
        elif proc.returncode == 109:
            return "timed out or memory limit exceeded"
        elif proc.returncode == 255:
            return "permission denied (root required)"
        elif proc.returncode:
            return f"unknown error, code: {proc.returncode}"
        else:
            return "unknown error, no error code"

        return output
