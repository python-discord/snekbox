import os
from importlib import metadata

DEBUG = os.environ.get("SNEKBOX_DEBUG", False)

try:
    __version__ = metadata.version("snekbox")
except metadata.PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0.0+unknown"

from snekbox.api import SnekAPI  # noqa: E402
from snekbox.logging import init_logger, init_sentry  # noqa: E402
from snekbox.nsjail import NsJail  # noqa: E402

__all__ = ("NsJail", "SnekAPI", "DEBUG")

init_sentry(__version__)
init_logger(DEBUG)
