import os
import re
import json
import time
import requests
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
import urllib3
from config import Config
from logger import get_logger

logger = get_logger(__name__)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class AudioScraper:
    def __init__(self, request_interval: float = None):
        self.config = Config()
        self.request_interval = request_interval or self.config.REQUEST_INTERVAL
    
    def save_to_json(self, audio_infos: List[Dict], filename: str = None) -> bool:
        filename = filename or self.config.JSON_OUTPUT_FILE
        try:
            data = {
                "metadata": {
                    "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "total_count": len(audio_infos),
                    "version": "1.0"
                },
                "audio_list": audio_infos
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"音频信息已保存到: {os.path.abspath(filename)}")
            logger.info(f"共保存 {len(audio_infos)} 个音频信息")
            return True
            
        except Exception as e:
            logger.error(f"保存JSON文件失败: {e}")
            return False
    
    def load_from_json(self, filename: str = None) -> Optional[List[Dict]]:
        filename = filename or self.config.JSON_OUTPUT_FILE
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if "audio_list" in data:
                audio_infos = data["audio_list"]
                logger.info(f"从 {filename} 加载了 {len(audio_infos)} 个音频信息")
                return audio_infos
            elif isinstance(data, list):
                return data
            else:
                logger.warning("JSON文件格式不正确")
                return None
                
        except FileNotFoundError:
            logger.error(f"文件不存在: {filename}")
            return None
        except json.JSONDecodeError:
            logger.error(f"JSON文件格式错误: {filename}")
            return None
        except Exception as e:
            logger.error(f"加载JSON文件失败: {e}")
            return None
    
    def init_session(self) -> bool:
        try:
            config = Config()
            response = requests.get(
                config.BASE_URL + "/", 
                headers=Config.get_headers(), 
                timeout=config.REQUEST_TIMEOUT, 
                verify=False
            )
            response.raise_for_status()
            logger.info(f"成功初始化会话，获取网页内容: {len(response.text)} 字符")
            return True
        except Exception as e:
            logger.error(f"初始化会话失败: {e}")
            return False
    
    def process_urls(self, urls: List[str]) -> List[Dict]:
        audio_infos = []
        
        for i, url in enumerate(urls):
            logger.info(f"正在处理URL ({i+1}/{len(urls)}): {url}")
            retry = self.config.MAX_RETRIES
            
            while retry:
                try:
                    audio_info = self.extract_audio_info(url)
                    if audio_info:
                        audio_infos.append(audio_info)
                        logger.info(f"✓ 成功提取音频信息: {audio_info.get('name')}")
                        
                        if i < len(urls) - 1:
                            time.sleep(self.request_interval)
                        break
                    else:
                        logger.warning(f"✗ 无法提取音频信息: {url}")
                        retry -= 1
                        
                except Exception as e:
                    logger.error(f"处理URL {url} 时发生错误: {e}")
                    if i < len(urls) - 1:
                        time.sleep(self.request_interval)
        
        return audio_infos
    
    def extract_audio_info(self, url: str) -> Optional[Dict]:
        max_retries = self.config.MAX_RETRIES
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                response = requests.get(
                    url, 
                    headers=Config.get_headers(), 
                    timeout=self.config.REQUEST_TIMEOUT, 
                    verify=False
                )
                response.raise_for_status()
                audio_info = self.extract_audio_from_html(response.text)
                
                if audio_info:
                    return audio_info
                
                logger.warning(f"解析失败，尝试 {retry_count + 1}/{max_retries}: {url}")
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(self.request_interval)
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"网络请求失败，尝试 {retry_count + 1}/{max_retries}: {e}")
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(self.request_interval)
            except Exception as e:
                logger.warning(f"提取音频信息时发生错误，尝试 {retry_count + 1}/{max_retries}: {e}")
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(self.request_interval)
        
        logger.error(f"达到最大重试次数 {max_retries}，解析失败: {url}")
        return None
    
    def extract_audio_from_html(self, html_content: str) -> Optional[Dict]:
        soup = BeautifulSoup(html_content, 'html.parser')
        scripts = soup.find_all('script')
        
        for script in scripts:
            if script.string:
                audio_config = self._extract_from_script(script.string)
                if audio_config:
                    return audio_config
        
        all_text = str(soup)
        return self._extract_from_script(all_text)
    
    def _extract_from_script(self, content: str) -> Optional[Dict]:
        patterns = [
            (r'audio:\s*(\[[\s\S]*?\])', self._parse_json_config),
            (r'new APlayer\s*\([\s\S]*?audio:\s*\[([\s\S]*?)\][\s\S]*?\)', self._parse_direct_config),
            (r'name:\s*[\'"]([^\'"]+)[\'"][\s\S]*?artist:\s*[\'"]([^\'"]+)[\'"][\s\S]*?url:\s*[\'"]([^\'"]+)[\'"]', 
             self._parse_simple_config),
        ]
        
        for pattern, parser in patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                result = parser(match)
                if result:
                    return result
        
        return None
    
    def _parse_json_config(self, match) -> Optional[Dict]:
        try:
            audio_config_str = match.group(1).replace("'", '"')
            audio_config_str = re.sub(r',\s*\]', ']', audio_config_str)
            
            audio_config = json.loads(audio_config_str)
            if isinstance(audio_config, list) and len(audio_config) > 0:
                audio_info = audio_config[0]
                return {
                    'name': audio_info.get('name', '未知名称'),
                    'artist': audio_info.get('artist', '未知艺术家'),
                    'url': audio_info.get('url', '')
                }
        except (json.JSONDecodeError, AttributeError, IndexError):
            pass
        
        return None
    
    def _parse_direct_config(self, match) -> Optional[Dict]:
        config_content = match.group(1)
        
        name_match = re.search(r"name:\s*['\"]([^'\"]*)['\"]", config_content)
        artist_match = re.search(r"artist:\s*['\"]([^'\"]*)['\"]", config_content)
        url_match = re.search(r"url:\s*['\"]([^'\"]*)['\"]", config_content)
        
        if name_match and artist_match and url_match:
            return {
                'name': name_match.group(1),
                'artist': artist_match.group(1),
                'url': url_match.group(1)
            }
        
        return None
    
    def _parse_simple_config(self, match) -> Optional[Dict]:
        return {
            'name': match.group(1),
            'artist': match.group(2),
            'url': match.group(3)
        }