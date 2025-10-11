#!/usr/bin/env bash
set -euxo pipefail
shopt -s inherit_errexit

py_version="${1}"

# Install Python interpreter under e.g. /snekbin/python/3.13/ (no patch version)
# By dropping everything after, and including, the last period or hyphen.
install_path="${py_version%[-.]*}"

# Ensure the suffix letter is retained for free-threaded or JIT versions of Python.
if [[ $py_version == *t ]]; then
    install_path+="t"
fi

if [[ $py_version == *j ]]; then
    # Enable JIT mode when passed a version that ends with a "j"
    install_path+="j"
    py_version="${py_version%j}"
    PYTHON_CONFIGURE_OPTS+=" --enable-experimental-jit"
fi

"${PYENV_ROOT}/plugins/python-build/bin/python-build" \
    "${py_version}" \
    "/snekbin/python/${install_path}"
"/snekbin/python/${install_path}/bin/python" -m pip install -U pip

# Clean up some unnecessary files to reduce image size bloat.
find /snekbin/python/ -depth \
\( \
    \( -type d -a \( \
        -name test -o -name tests -o -name idle_test \
    \) \) \
    -o \( -type f -a \( \
        -name '*.pyc' -o -name '*.pyo' -o -name 'libpython*.a' \
    \) \) \
\) -exec rm -rf '{}' +
