import re
from typing import List, Dict, Optional
from config import Config
from logger import get_logger

logger = get_logger(__name__)


class ChapterInfo:
    def __init__(self, chapter_id: str, index: int, title: str, href: str = ""):
        self.chapter_id = chapter_id
        self.index = index
        self.title = title
        self.href = href
    
    def to_dict(self) -> Dict:
        return {
            'chapter_id': self.chapter_id,
            'index': self.index,
            'title': self.title,
            'href': self.href
        }
    
    def __repr__(self):
        return f"ChapterInfo(index={self.index}, chapter_id='{self.chapter_id}', title='{self.title}')"


class LinkExtractor:
    @staticmethod
    def extract_play_content(text: str) -> List[str]:
        pattern = r'/play/(.*?)\.html'
        return re.findall(pattern, text)
    
    @staticmethod
    def extract_with_context(text: str, context_chars: int = 50) -> List[Dict]:
        pattern = r'/play/(.*?)\.html'
        results = []
        
        for match in re.finditer(pattern, text):
            content = match.group(1)
            start_pos = max(0, match.start() - context_chars)
            end_pos = min(len(text), match.end() + context_chars)
            context = text[start_pos:end_pos]
            
            results.append({
                'content': content,
                'start_position': match.start(),
                'end_position': match.end(),
                'context': context
            })
        
        return results
    
    @staticmethod
    def extract_chapters(text: str) -> List[ChapterInfo]:
        pattern = r'<a\s+id="chapter-pos-(\d+)"\s+href="(/play/(\d+)/(\d+)\.html)"[^>]*>.*?<span\s+class="text-xs[^"]*"\s*>(\d+)\.</span>.*?<span\s+class="text-sm[^"]*"\s*>([^<]+)</span>.*?</a>'
        
        results = []
        for match in re.finditer(pattern, text, re.DOTALL):
            index = int(match.group(1))
            href = match.group(2)
            book_id = match.group(3)
            chapter_num = match.group(4)
            chapter_id = f"{book_id}/{chapter_num}"
            title = match.group(6).strip()
            
            results.append(ChapterInfo(
                chapter_id=chapter_id,
                index=index,
                title=title,
                href=href
            ))
        
        return results
    
    @staticmethod
    def extract_chapters_as_dict(text: str) -> List[Dict]:
        chapters = LinkExtractor.extract_chapters(text)
        return [chapter.to_dict() for chapter in chapters]
    
    @staticmethod
    def build_play_urls(play_ids: List[str]) -> List[str]:
        config = Config()
        return [config.PLAY_URL_TEMPLATE.format(pid) for pid in play_ids]
    
    @staticmethod
    def extract_from_file(input_file: str, output_file: Optional[str] = None) -> List[str]:
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            matches = LinkExtractor.extract_play_content(content)
            
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    for match in matches:
                        f.write(f"{match}\n")
                logger.info(f"提取完成！结果已保存到 {output_file}")
            
            return matches
        except FileNotFoundError:
            logger.error(f"错误：找不到文件 {input_file}")
            return []
        except Exception as e:
            logger.error(f"发生错误：{e}")
            return []