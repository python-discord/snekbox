nsjpy() {
    local nsj_args=""
    while [ "$#" -gt 1 ]; do
        nsj_args="${nsj_args:+${nsj_args} }$1"
        shift
    done

    mkdir -p /sys/fs/cgroup/pids/NSJAIL
    mkdir -p /sys/fs/cgroup/memory/NSJAIL
    nsjail \
        -Mo \
        --rlimit_as 700 \
        --chroot / \
        -E LANG=en_US.UTF-8 \
        -R/usr -R/lib -R/lib64 \
        --user nobody \
        --group nogroup \
        --time_limit 2 \
        --disable_proc \
        --iface_no_lo \
        --cgroup_pids_max=1 \
        --cgroup_mem_max=52428800 \
        $nsj_args -- \
        /snekbox/.venv/bin/python3 -Iq -c "$@"
}
