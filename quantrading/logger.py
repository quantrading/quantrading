import logging
from logging.handlers import RotatingFileHandler

PRINT_LOG = False

LOG_FILE_PATH = "./log/logging.log"
DEFAULT_LOG_FORMAT = "[%(asctime)s][%(levelname)s|%(filename)s:%(funcName)s:%(lineno)s] >> %(message)s"
file_max_byte = 1024 * 1024 * 100

logger = logging.getLogger("myLogger")
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter(DEFAULT_LOG_FORMAT)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)
file_handler = RotatingFileHandler(LOG_FILE_PATH, maxBytes=file_max_byte, backupCount=10)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


BACKTEST_LOG_FORMAT = "[%(levelname)s|%(filename)s:%(funcName)s:%(lineno)s] >> %(message)s"
bt_logger = logging.getLogger("backtest")
file_max_byte = 1024 * 1024 * 100


bt_logger.setLevel(logging.DEBUG)

formatter = logging.Formatter(BACKTEST_LOG_FORMAT)

if PRINT_LOG:
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    bt_logger.addHandler(stream_handler)

file_handler = RotatingFileHandler(LOG_FILE_PATH, maxBytes=file_max_byte, backupCount=10)
file_handler.setFormatter(formatter)
bt_logger.addHandler(file_handler)
