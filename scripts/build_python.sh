#!/usr/bin/env bash
set -euxo pipefail
shopt -s inherit_errexit

py_version="${1}"

# Install Python interpreter under e.g. /lang/python/3.11/ (no patch version).
"${PYENV_ROOT}/plugins/python-build/bin/python-build" \
    "${py_version}" \
    "/lang/python/${py_version%[-.]*}"
"/lang/python/${py_version%[-.]*}/bin/python" -m pip install -U pip

# Clean up some unnecessary files to reduce image size bloat.
find /lang/python/ -depth \
\( \
    \( -type d -a \( \
        -name test -o -name tests -o -name idle_test \
    \) \) \
    -o \( -type f -a \( \
        -name '*.pyc' -o -name '*.pyo' -o -name 'libpython*.a' \
    \) \) \
\) -exec rm -rf '{}' +
