"""
日志模块 - 提供可配置的日志系统，支持动态级别调整和多输出目标
"""
import logging
import os
import sys
import threading
from datetime import datetime
from enum import IntEnum
from typing import Optional, Dict, Any, Union
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler


class LogLevel(IntEnum):
    """
    日志级别枚举，按优先级排序
    """
    NOTSET = 0
    DEBUG = 10
    INFO = 20
    WARN = 30
    ERROR = 40
    FATAL = 50
    CRITICAL = 50
    OFF = 100


class LogLevelFilter(logging.Filter):
    """
    日志级别过滤器，确保只有达到或超过当前设置级别的日志消息才会被记录
    """
    def __init__(self, min_level: LogLevel = LogLevel.DEBUG):
        super().__init__()
        self._min_level = min_level

    @property
    def min_level(self) -> LogLevel:
        return self._min_level

    @min_level.setter
    def min_level(self, level: LogLevel):
        if isinstance(level, str):
            level = LogLevel[level.upper()]
        self._min_level = level

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno >= self._min_level


class ColoredConsoleHandler(logging.StreamHandler):
    """
    自定义控制台处理器，支持彩色输出
    """
    COLORS = {
        'DEBUG': '\033[36m',
        'INFO': '\033[32m',
        'WARNING': '\033[33m',
        'WARN': '\033[33m',
        'ERROR': '\033[31m',
        'FATAL': '\033[35m',
        'CRITICAL': '\033[35m',
    }
    RESET = '\033[0m'

    def __init__(self, use_color: bool = True):
        super().__init__(sys.stdout)
        self.use_color = use_color and sys.stdout.isatty()

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            if self.use_color:
                color = self.COLORS.get(record.levelname, '')
                msg = f"{color}{msg}{self.RESET}"
            self.stream.write(msg + '\n')
            self.flush()
        except Exception:
            self.handleError(record)


class LogFormatter(logging.Formatter):
    """
    自定义日志格式化器
    """
    DEFAULT_FORMAT = '%(asctime)s [%(levelname)s] [%(name)s] %(message)s'
    SIMPLE_FORMAT = '%(levelname)s: %(message)s'

    def __init__(
        self,
        fmt: Optional[str] = None,
        datefmt: str = '%Y-%m-%d %H:%M:%S',
        style: str = '%'
    ):
        super().__init__(fmt or self.DEFAULT_FORMAT, datefmt, style)


class Logger:
    """
    功能完善的日志类，支持动态级别调整和多输出目标
    """
    _instance_lock = threading.Lock()
    _instances: Dict[str, 'Logger'] = {}

    def __new__(cls, name: str = 'app', *args, **kwargs):
        with cls._instance_lock:
            if name not in cls._instances:
                cls._instances[name] = super().__new__(cls)
                cls._instances[name]._initialized = False
            return cls._instances[name]

    def __init__(self, name: str = 'app', config: Optional[Dict[str, Any]] = None):
        if self._initialized and hasattr(self, '_config'):
            return

        self._name = name
        self._logger = logging.getLogger(name)
        self._logger.setLevel(LogLevel.DEBUG)
        self._logger.handlers.clear()

        self._config = config or {}
        self._level_filter = LogLevelFilter(LogLevel.DEBUG)
        self._handlers: Dict[str, logging.Handler] = {}
        self._lock = threading.RLock()

        self._setup_handlers()
        self._initialized = True

    def _setup_handlers(self):
        """根据配置设置处理器"""
        console_config = self._config.get('console', {})
        if console_config.get('enabled', True):
            self.add_console_handler(
                use_color=console_config.get('use_color', True),
                level=console_config.get('level', 'DEBUG'),
                format_string=console_config.get('format')
            )

        file_config = self._config.get('file', {})
        if file_config.get('enabled', False):
            self.add_file_handler(
                filename=file_config.get('filename', f'{self._name}.log'),
                level=file_config.get('level', 'DEBUG'),
                max_bytes=file_config.get('max_bytes', 10 * 1024 * 1024),
                backup_count=file_config.get('backup_count', 5),
                format_string=file_config.get('format')
            )

        timed_file_config = self._config.get('timed_file', {})
        if timed_file_config.get('enabled', False):
            self.add_timed_file_handler(
                filename=timed_file_config.get('filename', f'{self._name}.log'),
                level=timed_file_config.get('level', 'DEBUG'),
                when=timed_file_config.get('when', 'midnight'),
                interval=timed_file_config.get('interval', 1),
                backup_count=timed_file_config.get('backup_count', 7),
                format_string=timed_file_config.get('format')
            )

    def add_console_handler(
        self,
        use_color: bool = True,
        level: Union[str, LogLevel] = LogLevel.DEBUG,
        format_string: Optional[str] = None
    ) -> 'Logger':
        """添加控制台处理器"""
        with self._lock:
            if 'console' in self._handlers:
                self._logger.removeHandler(self._handlers['console'])

            handler = ColoredConsoleHandler(use_color=use_color)
            handler.setFormatter(LogFormatter(fmt=format_string))
            handler.setLevel(self._get_level_value(level))
            handler.addFilter(self._level_filter)

            self._logger.addHandler(handler)
            self._handlers['console'] = handler

        return self

    def add_file_handler(
        self,
        filename: str,
        level: Union[str, LogLevel] = LogLevel.DEBUG,
        max_bytes: int = 10 * 1024 * 1024,
        backup_count: int = 5,
        format_string: Optional[str] = None,
        encoding: str = 'utf-8'
    ) -> 'Logger':
        """添加文件处理器（支持滚动）"""
        with self._lock:
            if 'file' in self._handlers:
                self._handlers['file'].close()
                self._logger.removeHandler(self._handlers['file'])

            os.makedirs(os.path.dirname(filename) or '.', exist_ok=True)

            handler = RotatingFileHandler(
                filename=filename,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding=encoding
            )
            handler.setFormatter(LogFormatter(fmt=format_string))
            handler.setLevel(self._get_level_value(level))
            handler.addFilter(self._level_filter)

            self._logger.addHandler(handler)
            self._handlers['file'] = handler

        return self

    def add_timed_file_handler(
        self,
        filename: str,
        level: Union[str, LogLevel] = LogLevel.DEBUG,
        when: str = 'midnight',
        interval: int = 1,
        backup_count: int = 7,
        format_string: Optional[str] = None,
        encoding: str = 'utf-8'
    ) -> 'Logger':
        """添加时间滚动文件处理器"""
        with self._lock:
            handler_name = f'timed_file_{filename}'
            if handler_name in self._handlers:
                self._handlers[handler_name].close()
                self._logger.removeHandler(self._handlers[handler_name])

            os.makedirs(os.path.dirname(filename) or '.', exist_ok=True)

            handler = TimedRotatingFileHandler(
                filename=filename,
                when=when,
                interval=interval,
                backupCount=backup_count,
                encoding=encoding
            )
            handler.setFormatter(LogFormatter(fmt=format_string))
            handler.setLevel(self._get_level_value(level))
            handler.addFilter(self._level_filter)

            self._logger.addHandler(handler)
            self._handlers[handler_name] = handler

        return self

    def remove_handler(self, handler_name: str) -> 'Logger':
        """移除指定处理器"""
        with self._lock:
            if handler_name in self._handlers:
                handler = self._handlers[handler_name]
                handler.close()
                self._logger.removeHandler(handler)
                del self._handlers[handler_name]
        return self

    def set_level(self, level: Union[str, LogLevel]) -> 'Logger':
        """
        动态设置日志级别
        :param level: 日志级别（字符串或LogLevel枚举）
        """
        with self._lock:
            if isinstance(level, str):
                level = LogLevel[level.upper()]
            self._level_filter.min_level = level

            for handler in self._handlers.values():
                handler.setLevel(level)

        return self

    def get_level(self) -> LogLevel:
        """获取当前日志级别"""
        return self._level_filter.min_level

    def _get_level_value(self, level: Union[str, LogLevel]) -> int:
        """获取日志级别数值"""
        if isinstance(level, str):
            return LogLevel[level.upper()]
        return int(level)

    def debug(self, message: str, **kwargs):
        """记录调试级别日志"""
        self._logger.debug(message, extra=kwargs)

    def info(self, message: str, **kwargs):
        """记录信息级别日志"""
        self._logger.info(message, extra=kwargs)

    def warning(self, message: str, **kwargs):
        """记录警告级别日志"""
        self._logger.warning(message, extra=kwargs)

    def warn(self, message: str, **kwargs):
        """记录警告级别日志（别名）"""
        self.warning(message, **kwargs)

    def error(self, message: str, **kwargs):
        """记录错误级别日志"""
        self._logger.error(message, extra=kwargs)

    def fatal(self, message: str, **kwargs):
        """记录致命级别日志"""
        self._logger.fatal(message, extra=kwargs)

    def critical(self, message: str, **kwargs):
        """记录严重级别日志"""
        self._logger.critical(message, extra=kwargs)

    def log(self, level: Union[str, LogLevel], message: str, **kwargs):
        """通用日志记录方法"""
        level_value = self._get_level_value(level)
        self._logger.log(level_value, message, extra=kwargs)

    def is_enabled_for(self, level: Union[str, LogLevel]) -> bool:
        """检查指定级别是否启用"""
        if isinstance(level, str):
            level = LogLevel[level.upper()]
        return level >= self.get_level()

    @classmethod
    def get_logger(cls, name: str = 'app', config: Optional[Dict[str, Any]] = None) -> 'Logger':
        """
        获取日志实例（单例模式）
        :param name: 日志器名称
        :param config: 配置字典
        """
        return cls(name, config)

    @classmethod
    def reset_instance(cls, name: str = 'app'):
        """重置指定日志实例（用于测试）"""
        with cls._instance_lock:
            if name in cls._instances:
                instance = cls._instances[name]
                if hasattr(instance, '_handlers'):
                    for handler in instance._handlers.values():
                        handler.close()
                instance._logger.handlers.clear()
                del cls._instances[name]


def get_logger(name: str = 'app', config: Optional[Dict[str, Any]] = None) -> Logger:
    """
    获取日志实例的便捷函数
    :param name: 日志器名称
    :param config: 配置字典
    """
    return Logger.get_logger(name, config)


def set_log_level(level: Union[str, LogLevel], logger_name: str = 'app'):
    """
    动态设置全局日志级别
    :param level: 日志级别
    :param logger_name: 日志器名称
    """
    logger = Logger.get_logger(logger_name)
    logger.set_level(level)


def get_log_level(logger_name: str = 'app') -> LogLevel:
    """
    获取当前日志级别
    :param logger_name: 日志器名称
    """
    logger = Logger.get_logger(logger_name)
    return logger.get_level()
