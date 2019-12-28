nsjpy() {
    local MEM_MAX=52428800

    # All arguments except the last are considered to be for NsJail, not Python.
    local nsj_args=""
    while [ "$#" -gt 1 ]; do
        nsj_args="${nsj_args:+${nsj_args} }$1"
        shift
    done

    # Set up cgroups and disable memory swapping.
    mkdir -p /sys/fs/cgroup/pids/NSJAIL
    mkdir -p /sys/fs/cgroup/memory/NSJAIL
    echo "${MEM_MAX}" > /sys/fs/cgroup/memory/NSJAIL/memory.limit_in_bytes
    echo "${MEM_MAX}" > /sys/fs/cgroup/memory/NSJAIL/memory.memsw.limit_in_bytes

    nsjail \
        --config "${NSJAIL_CFG:-/snekbox/snekbox.cfg}" \
        $nsj_args -- \
        /snekbox/.venv/bin/python3 -Iq -c "$@"
}
