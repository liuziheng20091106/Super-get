import os
import logging
from datetime import datetime


LOG_DIR = "log"
LOG_LEVEL = logging.DEBUG
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


def _get_log_file_path():
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    today = datetime.now().strftime('%Y-%m-%d')
    return os.path.join(LOG_DIR, f"{today}.logs")


def setup_logger(name=None):
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)

    file_handler = logging.FileHandler(_get_log_file_path(), encoding='utf-8')
    file_handler.setLevel(LOG_LEVEL)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(LOG_LEVEL)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def get_logger(name=None):
    return setup_logger(name)