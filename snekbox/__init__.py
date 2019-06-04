import logging
import os

from gunicorn import glogging

DEBUG = os.environ.get("DEBUG", False)


class GunicornLogger(glogging.Logger):
    """Logger for Gunicorn with custom formatting and support for the DEBUG environment variable."""

    error_fmt = "%(asctime)s | %(process)5s | %(name)30s | %(levelname)8s | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    def setup(self, cfg):
        """Set up loggers and set error logger's level to DEBUG if the DEBUG env var is set."""
        super().setup(cfg)

        if DEBUG:
            self.loglevel = logging.DEBUG
        else:
            self.loglevel = self.LOG_LEVELS.get(cfg.loglevel.lower(), logging.INFO)

        self.error_log.setLevel(self.loglevel)
