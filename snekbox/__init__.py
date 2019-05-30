import logging
import sys

logformat = logging.Formatter(fmt="[%(asctime)s] [%(process)s] [%(levelname)s] %(message)s",
                              datefmt="%Y-%m-%d %H:%M:%S %z")
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
console = logging.StreamHandler(sys.stdout)
console.setFormatter(logformat)
log.addHandler(console)
