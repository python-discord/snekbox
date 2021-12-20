import logging
import uuid
from pathlib import Path

from snekbox.config_pb2 import NsJailConfig

log = logging.getLogger(__name__)


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


def get_version(config: NsJailConfig) -> int:
    """
    Examine the filesystem and return the guessed cgroup version.

    Fall back to use_cgroupv2 in the NsJail config if either both v1 and v2 seem to be enabled,
    or neither seem to be enabled.
    """
    cgroup_mounts = (
        config.cgroup_mem_mount,
        config.cgroup_pids_mount,
        config.cgroup_net_cls_mount,
        config.cgroup_cpu_mount
    )
    v1_exists = any(Path(mount).exists() for mount in cgroup_mounts)

    controllers_path = Path(config.cgroupv2_mount, "cgroup.controllers")
    v2_exists = controllers_path.exists()

    config_version = 2 if config.use_cgroupv2 else 1

    if v1_exists and v2_exists:
        # Probably hybrid mode. Use whatever is set in the config.
        return config_version
    elif v1_exists:
        return 1
    elif v2_exists:
        return 2
    else:
        log.warning(
            f"Neither the cgroupv1 controller mounts, nor {str(controllers_path)!r} exists. "
            "Either cgroup_xxx_mount and cgroupv2_mount are misconfigured, or all "
            "corresponding v1 controllers are disabled on the system. "
            "Falling back to the use_cgroupv2 NsJail setting."
        )
        return config_version
