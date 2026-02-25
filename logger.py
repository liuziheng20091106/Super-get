import os
import logging
import traceback
from datetime import datetime
from config import Config


LOG_DIR = "log"
CRASH_DIR = "log"
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


def _get_log_level():
    """根据配置获取日志级别"""
    if Config.DEBUG:
        return logging.DEBUG
    return logging.INFO


def _get_log_file_path():
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    today = datetime.now().strftime('%Y-%m-%d')
    return os.path.join(LOG_DIR, f"{today}.logs")


def setup_logger(name=None):
    logger = logging.getLogger(name)
    log_level = _get_log_level()
    logger.setLevel(log_level)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)

    file_handler = logging.FileHandler(_get_log_file_path(), encoding='utf-8')
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    return logger


def get_logger(name=None):
    return setup_logger(name)


def _get_crash_file_path():
    if not os.path.exists(CRASH_DIR):
        os.makedirs(CRASH_DIR)
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    return os.path.join(CRASH_DIR, f"crash_{timestamp}.log")


def log_crash(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        return

    crash_info = []
    crash_info.append("=" * 60)
    crash_info.append(f"CRASH TIME: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    crash_info.append(f"EXCEPTION TYPE: {exc_type.__name__}")
    crash_info.append(f"EXCEPTION MESSAGE: {str(exc_value)}")
    crash_info.append("")
    crash_info.append("TRACEBACK:")
    crash_info.append("".join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
    crash_info.append("=" * 60)

    crash_content = "\n".join(crash_info)

    crash_file = _get_crash_file_path()
    with open(crash_file, 'w', encoding='utf-8') as f:
        f.write(crash_content)

    logger = get_logger("crash")
    logger.error(f"程序崩溃! 异常类型: {exc_type.__name__}, 消息: {str(exc_value)}")
    logger.error(f"详细崩溃信息已保存至: {crash_file}")