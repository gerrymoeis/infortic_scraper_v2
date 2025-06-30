import logging
import os
import json
from pythonjsonlogger import jsonlogger

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()

class ColoredFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[94m',     # Blue
        'INFO': '\033[92m',      # Green
        'WARNING': '\033[93m',   # Yellow
        'ERROR': '\033[91m',     # Red
        'CRITICAL': '\033[95m',  # Purple
    }
    RESET = '\033[0m'

    def format(self, record):
        log_msg = super(ColoredFormatter, self).format(record)
        return f"{self.COLORS.get(record.levelname, self.RESET)}{log_msg}{self.RESET}"


def get_logger():
    if not hasattr(get_logger, "logger"):
        # Create logger
        logger = logging.getLogger('app')
        logger.setLevel(LOG_LEVEL)

        # Create console handler
        ch = logging.StreamHandler()

        # Select formatter based on environment
        if os.getenv('ENV', 'development').lower() == 'production':
            formatter = jsonlogger.JsonFormatter()
        else:
            formatter = ColoredFormatter('%(levelname)s - %(message)s')

        ch.setFormatter(formatter)
        logger.addHandler(ch)

        # Store logger instance in function attribute
        get_logger.logger = logger

    return get_logger.logger

# Initialize early
logger = get_logger()
logger.debug('Logger initialized.')

