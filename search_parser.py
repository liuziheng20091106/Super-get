import re
import urllib.parse
import logging
from typing import List, Dict, Optional
from config import Config


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class SearchResult:
    def __init__(self, book_id: str, title: str, author: str, narrator: str, 
                 cover_url: str, description: str, url: str):
        self.book_id = book_id
        self.title = title
        self.author = author
        self.narrator = narrator
        self.cover_url = cover_url
        self.description = description
        self.url = url
    
    def to_dict(self):
        return {
            'book_id': self.book_id,
            'title': self.title,
            'author': self.author,
            'narrator': self.narrator,
            'cover_url': self.cover_url,
            'description': self.description,
            'url': self.url
        }
    
    def __repr__(self):
        return f"SearchResult(id={self.book_id}, title={self.title})"


class SearchParser:
    SEARCH_URL_TEMPLATE = "https://m.i275.com/search.php?q={keyword}"
    
    @classmethod
    def build_search_url(cls, keyword: str) -> str:
        encoded_keyword = urllib.parse.quote(keyword)
        return cls.SEARCH_URL_TEMPLATE.format(keyword=encoded_keyword)
    
    @classmethod
    def parse_search_results(cls, html_content: str) -> List[SearchResult]:
        results = []
        
        item_pattern = r'<a href="(/book/\d+\.html)"[^>]*>.*?</a>'
        
        for match in re.finditer(item_pattern, html_content, re.DOTALL):
            item_html = match.group(0)
            href = match.group(1)
            
            book_id_match = re.search(r'/book/(\d+)\.html', href)
            if not book_id_match:
                continue
            
            book_id = book_id_match.group(1)
            
            title_match = re.search(r'<h3[^>]*>([^<]+)</h3>', item_html)
            title = title_match.group(1).strip() if title_match else ""
            
            narrator_match = re.search(r'演播</span>([^<]+)</p>', item_html)
            narrator = narrator_match.group(1).strip() if narrator_match else ""
            
            author_match = re.search(r'作者</span>([^<]+)</p>', item_html)
            author = author_match.group(1).strip() if author_match else ""
            
            cover_match = re.search(r'<img src="([^"]+)"', item_html)
            cover_url = cover_match.group(1) if cover_match else ""
            
            desc_match = re.search(r'<p class="text-xs text-gray-400[^"]*"[^>]*>([^<]+)</p>', item_html)
            description = desc_match.group(1).strip() if desc_match else ""
            
            url = f"https://m.i275.com{href}"
            
            results.append(SearchResult(
                book_id=book_id,
                title=title,
                author=author,
                narrator=narrator,
                cover_url=cover_url,
                description=description,
                url=url
            ))
        
        return results
    
    @classmethod
    def get_search_result_count(cls, html_content: str) -> int:
        match = re.search(r'"text-purple-600 font-bold">"([^"]+)" 的结果 \((\d+)\)</span>', html_content)
        if match:
            return int(match.group(2))
        return 0


class SearchClient:
    def __init__(self):
        self.session = None
        self.init_session()
    
    def init_session(self):
        import requests
        self.session = requests.Session()
        headers = Config.get_headers()
        logger.debug(f"Config.get_headers() 返回: {headers}")
        self.session.headers.update(headers)
        logger.debug(f"Session headers: {self.session.headers}")
    
    def search(self, keyword: str) -> List[SearchResult]:
        url = SearchParser.build_search_url(keyword)
        logger.info(f"搜索URL: {url}")
        
        try:
            logger.debug("发送HTTP请求...")
            timeout = Config._get_config().get("request_timeout", 10)
            logger.debug(f"Timeout: {timeout}")
            response = self.session.get(
                url, 
                timeout=timeout
            )
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            logger.debug(f"响应状态码: {response.status_code}")
            logger.debug(f"响应内容长度: {len(response.text)}")
            
            return SearchParser.parse_search_results(response.text)
        except Exception as e:
            logger.error(f"搜索失败: {e}", exc_info=True)
            return []
    
    def search_from_file(self, file_path: str) -> List[SearchResult]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return SearchParser.parse_search_results(content)
        except Exception as e:
            print(f"读取文件失败: {e}")
            return []


if __name__ == "__main__":
    results = SearchClient().search_from_file("new/test.txt")
    for r in results:
        print(f"ID: {r.book_id}, Title: {r.title}, Narrator: {r.narrator}, Author: {r.author}")