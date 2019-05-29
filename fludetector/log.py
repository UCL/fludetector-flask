"""
Fludetector: website, REST API, and data processors for the Fludetector service from UCL.
(c) 2019, UCL <https://www.ucl.ac.uk/

This file is part of Fludetector

Fludetector is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Fludetector is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Fludetector.  If not, see <http://www.gnu.org/licenses/>.


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
