import logging
import uuid
from pathlib import Path

from snekbox.config_pb2 import NsJailConfig

__all__ = ("controller_exists", "is_enabled", "should_ignore_limit")

log = logging.getLogger(__name__)


def controller_exists(config: NsJailConfig, cgroup_version: int) -> bool:
    """Return True if the swap memory cgroup controller is enabled."""
    if cgroup_version == 1:
        return Path(config.cgroup_mem_mount, "memory.memsw.max_usage_in_bytes").exists()
    else:
        # Create a child cgroup because memory.swap isn't available in the root cgroup.
        child = Path(config.cgroupv2_mount, f"snekbox-temp-{uuid.uuid4()}")
        child.mkdir()
        swap_controller_exists = (child / "memory.swap.max").exists()
        child.rmdir()

        return swap_controller_exists


def is_enabled() -> bool:
    """Return True if the total size of swap memory is greater than 0."""
    with open("/proc/meminfo", "rb") as f:
        for line in f:
            name, value, *_ = line.split()
            if name == b"SwapTotal:":
                return value != b"0"

    log.warning("Couldn't determine if swap is on or off. Assuming it's off.")
    return False


def should_ignore_limit(config: NsJailConfig, cgroup_version: int) -> bool:
    """
    Return True if a swap limit should not be configured for NsJail.

    If the swap controller doesn't exist, then NsJail would fail when trying to limit the swap.
    It would attempt to write to a file that doesn't exist. In such case, the swap limit arguments
    should be set to their default values, so NsJail will avoid setting a swap limit.

    Log a warning if swap is enabled but the swap controller isn't enabled.
    """
    if config.cgroup_mem_max <= 0:
        return False

    if config.cgroup_mem_memsw_max <= 0 and config.cgroup_mem_swap_max < 0:
        log.warning("Memory is being limited, but swap memory is unlimited.")
        return False

    controller_missing = not controller_exists(config, cgroup_version)
    if is_enabled() and controller_missing:
        log.warning(
            "Swap memory is available, but the swap memory controller is not enabled. This is "
            "probably due to the CONFIG_MEMCG_SWAP or CONFIG_MEMCG_SWAP_ENABLED kernel "
            "parameters not being set. NsJail will not be able to limit memory effectively. "
            "Please turn off swap memory on the system, or enable the swap memory controller."
        )

    return controller_missing
