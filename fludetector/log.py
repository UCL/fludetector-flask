"""
This module sets up the logging for the project, basically making sure that
we don't fill the production machine up with logs.
"""
import logging
from logging.handlers import RotatingFileHandler

import logzero
from logzero import logger

MAX_BYTES = 1000000
BACKUP_COUNT = 5

# Change this if you don't want to see all the logging in the console
logzero.loglevel(logging.DEBUG)
# logzero.loglevel(logging.INFO)
# logzero.loglevel(logging.WARNING)
# logzero.loglevel(logging.ERROR)

# Log debug and up to the debug file
logzero.logfile('logs/debug.log', maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, loglevel=logging.DEBUG)

# Find the just added debug log handler so we can add it back in when it's removed
debug_handler = None
for handler in list(logger.handlers):
    if isinstance(handler, RotatingFileHandler) and hasattr(handler, logzero.LOGZERO_INTERNAL_LOGGER_ATTR):
        debug_handler = handler

# Add an error-only log handler, this will remove the debug one we just added
logzero.logfile('logs/error.log', maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, loglevel=logging.ERROR)

# Add the debug one back in
logger.addHandler(debug_handler)
