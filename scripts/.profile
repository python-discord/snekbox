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
        -Mo \
        --rlimit_as 700 \
        --chroot / \
        -E LANG=en_US.UTF-8 \
        -E OMP_NUM_THREADS=1 \
        -E OPENBLAS_NUM_THREADS=1 \
        -E MKL_NUM_THREADS=1 \
        -E VECLIB_MAXIMUM_THREADS=1 \
        -E NUMEXPR_NUM_THREADS=1 \
        -R/usr -R/lib -R/lib64 \
        --user 65534 \
        --group 65534 \
        --time_limit 2 \
        --disable_proc \
        --iface_no_lo \
        --cgroup_pids_max=1 \
        --cgroup_mem_max="${MEM_MAX}" \
        $nsj_args -- \
        /snekbox/.venv/bin/python3 -Iq -c "$@"
}
