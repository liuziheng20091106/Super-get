"""
配置管理模块 - 负责加载和管理配置文件
"""
import json
import os
from typing import Any, Dict, Optional


class Config:
    """
    配置管理类，支持从 JSON 文件加载配置和动态修改配置
    """
    _instance: Optional['Config'] = None

    def __new__(cls, config_path: Optional[str] = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_path: Optional[str] = None):
        if self._initialized:
            return

        self._config_path = config_path or self._get_default_config_path()
        self._config: Dict[str, Any] = {}
        self._load_config()
        self._initialized = True

    def _get_default_config_path(self) -> str:
        """获取默认配置文件路径"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        return os.path.join(project_root, 'config.json')

    def _load_config(self):
        """从 JSON 文件加载配置"""
        if not os.path.exists(self._config_path):
            self._config = self._get_default_config()
            self.save()
            return

        try:
            with open(self._config_path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"配置文件格式错误: {e}")
        except IOError as e:
            raise IOError(f"无法读取配置文件: {e}")

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "version": "1.0.1",
            "request_interval": 1,
            "request_timeout": 10,
            "max_retries": 3,
            "max_workers": 2,
            "download_timeout": 60,
            "default_download_dir": "downloads",
            "log_level": "INFO",
            "auto_sync": 1.0
        }

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        :param key: 配置键名
        :param default: 默认值
        :return: 配置值
        """
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value

    def set(self, key: str, value: Any):
        """
        设置配置值
        :param key: 配置键名（支持点号分隔的嵌套键）
        :param value: 配置值
        """
        keys = key.split('.')
        config = self._config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value

    def save(self, config_path: Optional[str] = None):
        """
        保存配置到文件
        :param config_path: 配置文件路径（可选，默认保存到原文件）
        """
        save_path = config_path or self._config_path
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
        except IOError as e:
            raise IOError(f"无法保存配置文件: {e}")

    def reload(self):
        """重新加载配置文件"""
        self._load_config()

    @property
    def request_interval(self) -> float:
        """请求间隔时间（秒）"""
        return self.get('request_interval', 0.5)

    @property
    def request_timeout(self) -> int:
        """请求超时时间（秒）"""
        return self.get('request_timeout', 10)

    @property
    def max_retries(self) -> int:
        """最大重试次数"""
        return self.get('max_retries', 3)

    @property
    def max_workers(self) -> int:
        """最大工作线程数"""
        return self.get('max_workers', 32)

    @property
    def download_timeout(self) -> int:
        """下载超时时间（秒）"""
        return self.get('download_timeout', 60)

    @property
    def default_download_dir(self) -> str:
        """默认下载目录"""
        return self.get('default_download_dir', 'downloads')

    @property
    def log_level(self) -> str:
        """日志级别"""
        return self.get('log_level', 'INFO')

    @property
    def version(self) -> str:
        """版本号"""
        return self.get('version', '1.0.1')

    @property
    def auto_sync(self) -> float:
        """自动同步间隔（小时）"""
        return self.get('auto_sync', 1.0)

    def to_dict(self) -> Dict[str, Any]:
        """将配置转换为字典"""
        return self._config.copy()


def get_config(config_path: Optional[str] = None) -> Config:
    """
    获取配置实例的便捷函数
    :param config_path: 配置文件路径（可选）
    :return: Config 实例
    """
    return Config(config_path)
