import logging

from gunicorn import glogging
from gunicorn.config import Config

from snekbox import DEBUG

from .init import FORMAT

__all__ = ("GunicornLogger",)


class GunicornLogger(glogging.Logger):
    """Logger for Gunicorn with custom formatting and support for the DEBUG environment variable."""

    error_fmt = FORMAT
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
