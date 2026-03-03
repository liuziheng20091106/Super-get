"""
旧版章节URL获取API
需要重构以使用当前环境的API客户端

由于是妥协方案，不应该大幅修改其他功能来进行适配。
当前准备通过api_client.py重定向到此文件来实现。
入口为get_chapter_url()
可用参数
chapter_id: 章节ID
book_id: 书籍ID
request_timeout: 请求超时时间（秒）
_is_retry: 是否重试（内部使用） 在这里没啥用


"""
import os
import re
import json
import time
import requests
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
import urllib3
from typing import Union





urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_default_config():
    """
    老客户端的配置文件，可以用来参考
    """
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

def get_headers(Cookies: str = ""):
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Cookie': Cookies
        }
#主要的类。但是这里或许需要换方法实现？

class AudioScraper:
    last_request_time = 0.0
    request_timeout = 10.0
    init_timeout = 15.0 * 60 
    Cookies = "PHPSESSID=bmjc7an8kau9cki8nut8048c03"
    

    def __init__(self, request_interval: float = 10):

        self.request_interval = request_interval
     
    def init_session(self) -> bool:
        try:

            response = requests.get(
                "https://i275.com", 
                headers=get_headers(self.Cookies), 
                timeout=self.request_timeout, 
                verify=False
            )
            response.raise_for_status()
            #self.logger.info(f"成功初始化会话，获取网页内容: {len(response.text)} 字符")
            return True
        except Exception as e:
            #self.logger.error(f"初始化会话失败: {e}")
            return False
    

    def extract_audio_info(self, url: str) -> Optional[str]:
            """
            这里理论上是主入口，但是可能需要初始化才能使用。
            下一步是如何全局初始化
            老API就是不咋地。
            """

        

            try:
                response = requests.get(
                    url, 
                    headers=get_headers(self.Cookies), 
                    timeout=self.request_timeout, 
                    verify=False
                )
                response.raise_for_status()
                #print(response.text)
                audio_info = self.extract_audio_from_html(response.text)
                
                if audio_info:
                    #print(audio_info)
                    return audio_info.get("url")

                    

            except Exception as e:
                #self.logger.warning(f"提取音频信息时发生错误，尝试 {retry_count + 1}/{max_retries}: {e}")
                #print(e)
                pass

        
            #self.logger.error(f"达到最大重试次数 {max_retries}，解析失败: {url}")
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
    
    
_AudioScraper = None

def get_chapter_url(chapter_id: int, book_id: int, request_timeout: float = 10, logger=None) -> Union[str, bool]:
    """
    获取章节URL
    
    """
    my_AudioScraper = init(request_timeout)
    if not my_AudioScraper:
        if logger:
            logger.error(f"[获取章节URL] 初始化失败, 章节ID: {chapter_id}, 书籍ID: {book_id}")
        return False
    if logger:
        logger.debug(f"[获取章节URL] 开始, 章节ID: {chapter_id}, 书籍ID: {book_id},url: https://i275.com/play/{book_id}/{chapter_id}.html")
    url = my_AudioScraper.extract_audio_info(f"https://i275.com/play/{book_id}/{chapter_id}.html")
    if logger:
        logger.debug(f"[获取章节URL] 解析成功, 章节ID: {chapter_id}, 书籍ID: {book_id}, url: {url}")
    if not url:
        if logger:
            logger.error(f"[获取章节URL] 解析失败, 章节ID: {chapter_id}, 书籍ID: {book_id}")
        return False
    return url

def init(request_timeout: float = 10) -> AudioScraper:
    """
    初始化引擎
    
    """
    global _AudioScraper
    if _AudioScraper is None:
        _AudioScraper = AudioScraper()
    _AudioScraper.request_timeout = request_timeout
    #print(time.time(), _AudioScraper.last_request_time)
    #print()
    #print(_AudioScraper.init_timeout)
    if time.time() - _AudioScraper.last_request_time > _AudioScraper.init_timeout:
        _AudioScraper.init_session()
        #print(f"初始化引擎")
        _AudioScraper.last_request_time = time.time()
    return _AudioScraper
