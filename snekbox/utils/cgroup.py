import logging
import uuid
from pathlib import Path

from snekbox.config_pb2 import NsJailConfig

log = logging.getLogger(__name__)

# If this file is present, cgroupv2 should be enabled
CGROUPV2_PROBE_PATH = Path("/sys/fs/cgroup/cgroup.controllers")


def create_dynamic(config: NsJailConfig) -> str:
    """
    Create a PID and memory cgroup for NsJail to use as the parent cgroup.

    Returns the name of the cgroup, located in the cgroup root.

    NsJail doesn't do this automatically because it requires privileges NsJail usually doesn't
    have.

    Disables memory swapping.
    """
    # Pick a name for the cgroup
    cgroup = "snekbox-" + str(uuid.uuid4())

    pids = Path(config.cgroup_pids_mount, cgroup)
    mem = Path(config.cgroup_mem_mount, cgroup)
    mem_max = str(config.cgroup_mem_max)

    pids.mkdir(parents=True, exist_ok=True)
    mem.mkdir(parents=True, exist_ok=True)

    # Swap limit cannot be set to a value lower than memory.limit_in_bytes.
    # Therefore, this must be set before the swap limit.
    #
    # Since child cgroups are dynamically created, the swap limit has to be set on the parent
    # instead so that children inherit it. Given the swap's dependency on the memory limit,
    # the memory limit must also be set on the parent. NsJail only sets the memory limit for
    # child cgroups, not the parent.
    (mem / "memory.limit_in_bytes").write_text(mem_max, encoding="utf-8")

    try:
        # Swap limit is specified as the sum of the memory and swap limits.
        # Therefore, setting it equal to the memory limit effectively disables swapping.
        (mem / "memory.memsw.limit_in_bytes").write_text(mem_max, encoding="utf-8")
    except PermissionError:
        log.warning(
            "Failed to set the memory swap limit for the cgroup. "
            "This is probably because CONFIG_MEMCG_SWAP or CONFIG_MEMCG_SWAP_ENABLED is unset. "
            "Please ensure swap memory is disabled on the system."
        )

    return cgroup


def probe_version() -> int:
    """Poll the filesystem and return the guessed cgroup version."""
    # Right now we check whenever the controller path exists
    version = 2 if CGROUPV2_PROBE_PATH.exists() else 1
    log.debug(f"Guessed cgroups version: {version}")
    return version
