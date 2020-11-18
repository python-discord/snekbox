import logging
import os
import sys

import sentry_sdk
from gunicorn import glogging
from gunicorn.config import Config
from sentry_sdk.integrations.falcon import FalconIntegration

DEBUG = os.environ.get("DEBUG", False)

# Add comment to invalidate cache partially
sentry_sdk.init(
    dsn=os.environ.get("SNEKBOX_SENTRY_DSN", ""),
    integrations=[FalconIntegration()],
    send_default_pii=True
)


class GunicornLogger(glogging.Logger):
    """Logger for Gunicorn with custom formatting and support for the DEBUG environment variable."""

    error_fmt = "%(asctime)s | %(process)5s | %(name)30s | %(levelname)8s | %(message)s"
    access_fmt = error_fmt
    datefmt = None  # Use the default ISO 8601 format

    def setup(self, cfg: Config) -> None:
        """
        Set up loggers and set error logger's level to DEBUG if the DEBUG env var is set.

        Note: Access and syslog handlers would need to be recreated to use a custom date format
        because they are created with an unspecified datefmt argument by default.
        """
        super().setup(cfg)

        if DEBUG:
            self.loglevel = logging.DEBUG
        else:
            self.loglevel = self.LOG_LEVELS.get(cfg.loglevel.lower(), logging.INFO)

        self.error_log.setLevel(self.loglevel)


log = logging.getLogger("snekbox")
log.setLevel(logging.DEBUG if DEBUG else logging.INFO)
log.propagate = True
formatter = logging.Formatter(GunicornLogger.error_fmt)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)
log.addHandler(handler)
