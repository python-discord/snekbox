#!/bin/bash
chmod +x binaries/nsjail2.6-ubuntu-x86_64
apt-get update
apt-get install libprotobuf-dev
echo $(pwd)/binaries/nsjail2.6-ubuntu-x86_64 -Mo --rlimit_as 700 --chroot / -E LANG=en_US.UTF-8 -R/usr -R/lib -R/lib64 --user nobody --group nogroup --time_limit 2 --disable_proc --iface_no_lo --quiet -- /usr/bin/python3.6 -ISq -c 'print("test")'
$(pwd)/binaries/nsjail2.6-ubuntu-x86_64 -Mo --rlimit_as 700 --chroot / -E LANG=en_US.UTF-8 -R/usr -R/lib -R/lib64 --user nobody --group nogroup --time_limit 2 --disable_proc --iface_no_lo --quiet -- /usr/bin/python3.6 -ISq -c 'print("test")'
