import os

from snekbox.utils.logging import init_logger, init_sentry

DEBUG = os.environ.get("DEBUG", False)

init_sentry()
init_logger(DEBUG)
