#!/usr/bin/env bash
set -euxo pipefail
shopt -s inherit_errexit

py_version="${1}"

# Install Python interpreter under /snekbin/python/3.X/ (no patch version).
# The version may have a `t` or `j` suffix for free-threading or JIT-enabled.
install_dir="/snekbin/python/${py_version}"

if [[ $py_version == *j ]]; then
    # Enable JIT mode when passed a version that ends with a "j".
    # One standalone Python build is used for both with and without JIT.
    # This requires setting an env var, which we set with a shell script that
    # runs the non-JIT install, so that install must already exist.
    real_exe="/snekbin/python/${py_version%j}/bin/python"
    if [[ ! -x $real_exe ]]; then
        echo "${real_exe} not found; install ${py_version%j} first" >&2
        exit 1
    fi
    mkdir -p "${install_dir}/bin"
    for exe in python python3; do
        printf '#!/bin/sh\nPYTHON_JIT=1 exec %s "$@"\n' "${real_exe}" > "${install_dir}/bin/${exe}"
        chmod +x "${install_dir}/bin/${exe}"
    done
    exit 0
fi

# Download a prebuilt interpreter with uv, then move it to its final location.
# The python-build-standalone distributions that uv installs are relocatable.
UV_PYTHON_INSTALL_DIR="$(mktemp -d)"
export UV_PYTHON_INSTALL_DIR
uv python install --no-bin "${py_version}"
py_exe="$(uv python find --no-project --managed-python "${py_version}")"
py_exe="$(readlink -f "${py_exe}")"

# We install packages into the user-site directory.
rm -f "${py_exe%/bin/*}"/lib/python*/EXTERNALLY-MANAGED

mv "${py_exe%/bin/*}" "${install_dir}"
rm -rf "${UV_PYTHON_INSTALL_DIR}"

"${install_dir}/bin/python" -m pip install -U pip

# Precompile bytecode, since it can't be written at runtime in the sandbox.
"${install_dir}/bin/python" -m compileall -q -j 0 "${install_dir}/lib"
