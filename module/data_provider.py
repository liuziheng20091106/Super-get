from dataclasses import dataclass, asdict
from typing import Optional, Any

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

    Chapters: list['ChapterInfo']

    def edit(self, **kwargs) -> None:
        """
        编辑书籍元数据，除 id 和 Chapters 外其他字段都可编辑
        """
        for key, value in kwargs.items():
            if key in ('id', 'Chapters'):
                continue
            if hasattr(self, key):
                setattr(self, key, value)

    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'BookInfo':
        """从字典创建实例"""
        chapters_data = data.pop('Chapters', [])
        chapters = [ChapterInfo.from_dict(c) for c in chapters_data]
        data['Chapters'] = chapters
        return cls(**data)


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

    def edit(self, **kwargs) -> None:
        """
        编辑章节元数据，除 chapterid 外其他字段都可编辑
        """
        for key, value in kwargs.items():
            if key == 'chapterid':
                continue
            if hasattr(self, key):
                setattr(self, key, value)

    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'ChapterInfo':
        """从字典创建实例"""
        return cls(**data)


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

    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'SearchResult':
        """从字典创建实例"""
        return cls(**data)
