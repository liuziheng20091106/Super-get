from dataclasses import dataclass

@dataclass
class BookInfo:
    """
    书籍信息
    """
    
    id: int
    count: int
    UpdateStatus: int
    Image: str
    Desc: str
    Title: str
    Anchor: str
    
    Chapters: list[ChapterInfo]
    
@dataclass
class ChapterInfo:
    """
    章节信息
    """
    
    chapterid: int
    position: int
    title: str
    time: str
    uploadDate: str
    url: int
    
    bookTitle: str
    bookid: int
    bookAnchor: str
    bookDesc: str
    bookImage: str
    
    downloaded: bool = False

@dataclass
class SearchResult:
    """
    搜索结果
    """

    id: int
    bookTitle: str
    bookDesc: str
    bookImage: str
    bookAnchor: str
    count: int
    UpdateStatus: int
    heat: int
