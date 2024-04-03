set -euo pipefail

export PYTHONUSERBASE=/snekbox/user_base
find /lang/python -mindepth 1 -maxdepth 1 -type d -print0 | xargs -0I{} bash -c \
    '{}/bin/python -m pip install --user -U -r requirements/eval-deps.pip' \;
