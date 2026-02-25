import os
import json

CONFIG_FILE = "config.json"

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), CONFIG_FILE)
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return get_default_config()

def get_default_config():
    return {
        "base_url": "https://i275.com",
        "play_url_template": "https://i275.com/play/{}.html",
        "cookie": "PHPSESSID=bmjc7an8kau9cki8nut8048c03",
        "request_interval": 0.1,
        "request_timeout": 10,
        "max_retries": 3,
        "max_workers": 32,
        "download_timeout": 60,
        "default_download_dir": "downloads",
        "debug": False
    }

def save_config(config):
    config_path = os.path.join(os.path.dirname(__file__), CONFIG_FILE)
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

_config = None

class Config:
    @staticmethod
    def _get_config():
        global _config
        if _config is None:
            _config = load_config()
        return _config
    
    @staticmethod
    def reload():
        global _config
        _config = load_config()
    
    @staticmethod
    def save():
        if _config:
            save_config(_config)
    
    @property
    def BASE_URL(self):
        return self._get_config().get("base_url", "https://i275.com")
    
    @property
    def PLAY_URL_TEMPLATE(self):
        return self._get_config().get("play_url_template", "https://i275.com/play/{}.html")
    
    @property
    def COOKIE(self):
        return self._get_config().get("cookie", "")
    
    @property
    def REQUEST_INTERVAL(self):
        return self._get_config().get("request_interval", 0.1)
    
    @property
    def REQUEST_TIMEOUT(self):
        return self._get_config().get("request_timeout", 10)
    
    @property
    def MAX_RETRIES(self):
        return self._get_config().get("max_retries", 3)
    
    @property
    def MAX_WORKERS(self):
        return self._get_config().get("max_workers", 32)
    
    @property
    def DOWNLOAD_TIMEOUT(self):
        return self._get_config().get("download_timeout", 60)
    
    @property
    def DEFAULT_DOWNLOAD_DIR(self):
        return self._get_config().get("default_download_dir", "downloads")
    
    @property
    def JSON_OUTPUT_FILE(self):
        return self._get_config().get("json_output_file", "audio_infos.json")
    
    @property
    def INPUT_FILE(self):
        return self._get_config().get("input_file", "input.txt")
    
    @property
    def OUTPUT_FILE(self):
        return self._get_config().get("output_file", "output.txt")

    @property
    def DEBUG(self):
        return self._get_config().get("debug", False)
    
    @classmethod
    def get_headers(cls):
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Cookie': cls._get_config().get("cookie", "")
        }
    
    @classmethod
    def get_all_config(cls):
        return cls._get_config()
    
    @classmethod
    def update_config(cls, key, value):
        config = cls._get_config()
        config[key] = value
        global _config
        _config = config
        save_config(config)
    
    @classmethod
    def update_multiple(cls, updates):
        config = cls._get_config()
        config.update(updates)
        global _config
        _config = config
        save_config(config)