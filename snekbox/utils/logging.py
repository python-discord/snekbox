import logging
import os
import sys

import sentry_sdk
from sentry_sdk.integrations.falcon import FalconIntegration

__all__ = ("FORMAT", "init_logger", "init_sentry")

FORMAT = "%(asctime)s | %(process)5s | %(name)30s | %(levelname)8s | %(message)s"


def init_logger(debug: bool) -> None:
    """Initialise the root logger with a handler that outputs to stdout."""
    log = logging.getLogger("snekbox")
    log.setLevel(logging.DEBUG if debug else logging.INFO)
    log.propagate = True

    formatter = logging.Formatter(FORMAT)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    log.addHandler(handler)


def init_sentry() -> None:
    """Initialise the Sentry SDK."""
    git_sha = os.environ.get("GIT_SHA", "development")
    sentry_sdk.init(
        dsn=os.environ.get("SNEKBOX_SENTRY_DSN", ""),
        integrations=[FalconIntegration()],
        send_default_pii=True,
        release=f"snekbox@{git_sha}"
    )
