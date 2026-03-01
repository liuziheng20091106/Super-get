"""
数据管理中间层
提供书籍和章节的完整管理功能

程序基本原理：
初始化->搜索获得结果->解析书籍详细与章节列表->提交下载任务

主要功能：
- 初始化:使用get_token和get_base_url获取基本参数
- 搜索(中转到search_books函数)
- 添加书籍到书籍列表(SearchResult -> BookInfo)
- 查询我的书籍列表(返回list[BookInfo])
- 保存书籍列表到json
- 从json加载书籍列表
- 获取/更新章节列表(根据chapterid去重，保留下载状态)
- 获取/更新书籍详细(覆盖除了Chapters外的内容)
- 编辑元数据
- 修改下载状态
- 获取未下载的章节列表
- 下载管理(多线程下载、暂停、恢复、取消)
- 定时同步任务
"""

import json
import os
from typing import Optional, Union, Any, cast
from module.data_provider import BookInfo, ChapterInfo, SearchResult
from module import api_client
from module.config import Config
from module.download_manager import DownloadManager
from module.sync_timer import SyncTimer


class Manager:
    """数据管理中间层"""

    def __init__(self, logger=None, config: Optional[Config] = None):
        """
        初始化管理器
        
        Args:
            logger: 日志记录器
            config: 配置对象，如果为None则自动从config.json加载
        """
        self.logger = logger
        self.config = config or Config()
        self.base_url: Optional[str] = None
        self.token: Optional[str] = None
        self.books: list[BookInfo] = []
        self._download_manager: Optional[DownloadManager] = None
        self._sync_timer: Optional[SyncTimer] = None
        self._init_params()
        self.load_from_json()

    def _init_params(self) -> None:
        """初始化基本参数"""
        self.base_url = self.get_base_url()
        if not self.base_url:
            raise RuntimeError("[管理器] 获取BaseURL失败")
        
        token = self.get_token()
        if not token:
            raise RuntimeError("[管理器] 获取Token失败")
        
        self.token = token
        
        if self.logger:
            self.logger.info(f"[管理器] 初始化成功, BaseURL: {self.base_url}")

    def get_base_url(self) -> Optional[str]:
        """
        获取API基础URL
        
        Returns:
            基础URL字符串，失败返回None
        """
        result = api_client.get_base_url(logger=self.logger)
        if isinstance(result, str):
            return result
        return None

    def get_token(self) -> Optional[str]:
        """
        获取认证Token
        
        Returns:
            Token字符串，失败返回None
        """
        result = api_client.get_token(logger=self.logger)
        if isinstance(result, str):
            return result
        return None

    def search_books(self, keyword: str) -> Union[list[SearchResult], bool]:
        """
        搜索书籍
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            SearchResult列表，失败返回False
        """
        if not self.base_url or not self.token:
            if self.logger:
                self.logger.error("[搜索书籍] BaseURL或Token未初始化")
            return False
        
        return api_client.search_books(
            self.base_url, 
            keyword, 
            self.token, 
            logger=self.logger
        )

    def add_book(self, search_result: SearchResult) -> bool:
        """
        添加书籍到书籍列表
        
        通过 get_book_detail 获取完整书籍信息
        
        Args:
            search_result: 搜索结果
            
        Returns:
            是否添加成功
        """
        for book in self.books:
            if book.id == search_result.id:
                if self.logger:
                    self.logger.info(f"[添加书籍] 书籍已存在: {search_result.bookTitle}")
                return False
        
        if not self.base_url:
            if self.logger:
                self.logger.error(f"[添加书籍] BaseURL未初始化")
            return False
        
        detail = api_client.get_book_detail(self.base_url, search_result.id, logger=self.logger)
        if detail is False or detail is None:
            if self.logger:
                self.logger.error(f"[添加书籍] 获取书籍详情失败: {search_result.id}")
            return False
        
        book_info = cast(BookInfo, detail)
        self.books.append(book_info)
        
        self.update_chapters(book_info)
        
        if self.logger:
            self.logger.info(f"[添加书籍] 添加成功: {book_info.Title}")
        return True

    def get_books(self) -> list[BookInfo]:
        """
        获取我的书籍列表
        
        Returns:
            书籍列表
        """
        return self.books

    def get_book_by_id(self, book_id: int) -> Optional[BookInfo]:
        """
        根据ID获取书籍
        
        Args:
            book_id: 书籍ID
            
        Returns:
            BookInfo或None
        """
        for book in self.books:
            if book.id == book_id:
                return book
        return None

    def remove_book(self, book: BookInfo) -> bool:
        """
        从书籍列表中移除书籍
        
        Args:
            book: 书籍信息
            
        Returns:
            是否移除成功
        """
        if book in self.books:
            self.books.remove(book)
            if self.logger:
                self.logger.info(f"[移除书籍] 移除成功: {book.Title}")
            return True
        return False

    def update_chapters(self, book: BookInfo) -> Union[list[ChapterInfo], bool]:
        """
        获取并更新书籍章节列表
        
        根据chapterid去重，保留原有下载状态
        
        Args:
            book: 书籍信息
            
        Returns:
            ChapterInfo列表，失败返回False
        """
        if not self.base_url:
            if self.logger:
                self.logger.error(f"[更新章节] BaseURL未初始化")
            return False
        
        chapters = api_client.get_chapter_list(self.base_url, book.id, logger=self.logger)
        if chapters is False or chapters is None:
            if self.logger:
                self.logger.error(f"[更新章节] 获取章节列表失败: {book.id}")
            return False
        
        chapter_list = cast(list[ChapterInfo], chapters)
        existing_chapters = {ch.chapterid: ch for ch in book.Chapters}
        
        new_chapters = []
        for new_ch in chapter_list:
            if new_ch.chapterid in existing_chapters:
                existing_ch = existing_chapters[new_ch.chapterid]
                new_ch.downloaded = existing_ch.downloaded
            new_chapters.append(new_ch)
        
        book.Chapters = new_chapters
        
        if self.logger:
            self.logger.info(f"[更新章节] 更新成功: {book.Title}, 章节数: {len(new_chapters)}")
        
        return new_chapters

    def update_book_detail(self, book: BookInfo) -> Union[BookInfo, bool]:
        """
        获取并更新书籍详细信息
        
        覆盖除了Chapters外的内容
        
        Args:
            book: 书籍信息
            
        Returns:
            BookInfo，失败返回False
        """
        if not self.base_url:
            if self.logger:
                self.logger.error(f"[更新详情] BaseURL未初始化")
            return False
        
        detail = api_client.get_book_detail(self.base_url, book.id, logger=self.logger)
        if detail is False or detail is None:
            if self.logger:
                self.logger.error(f"[更新详情] 获取详情失败: {book.id}")
            return False
        
        detail_info = cast(BookInfo, detail)
        old_chapters = book.Chapters
        book.id = detail_info.id
        book.count = detail_info.count
        book.UpdateStatus = detail_info.UpdateStatus
        book.Image = detail_info.Image
        book.Desc = detail_info.Desc
        book.Title = detail_info.Title
        book.Anchor = detail_info.Anchor
        book.Chapters = old_chapters
        
        if self.logger:
            self.logger.info(f"[更新详情] 更新成功: {book.Title}")
        
        return book

    def get_undownloaded_chapters(self, book: BookInfo) -> list[ChapterInfo]:
        """
        获取未下载的章节列表
        
        Args:
            book: 书籍信息
            
        Returns:
            未下载的章节列表
        """
        return [ch for ch in book.Chapters if not ch.downloaded]
    
    def len_downloaded_chapters(self, book: BookInfo) -> int:
        """
        获取已下载的章节数
        
        Args:
            book: 书籍信息
            
        Returns:
            已下载的章节数
        """
        return sum(1 for ch in book.Chapters if ch.downloaded)

    def set_chapter_downloaded(self, chapter: ChapterInfo, downloaded: bool = True) -> None:
        """
        设置章节下载状态
        
        Args:
            chapter: 章节信息
            downloaded: 是否已下载
        """
        chapter.downloaded = downloaded
        if self.logger:
            self.logger.info(f"[设置下载状态] 章节: {chapter.title}, 状态: {downloaded}")

    def save_to_json(self, file_path: str = "data/books.json") -> bool:
        """
        保存书籍列表到JSON文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否保存成功
        """
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            timer_book_ids = []
            if self._sync_timer:
                timer_book_ids = self._sync_timer.get_book_ids()
            
            data = {
                "base_url": self.base_url,
                "token": self.token,
                "books": [book.to_dict() for book in self.books],
                "timer_book_ids": timer_book_ids,
                "auto_sync": self.config.auto_sync
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            if self.logger:
                self.logger.info(f"[保存数据] 保存成功: {file_path}, 书籍数: {len(self.books)}, 定时任务书籍ID: {timer_book_ids}")
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"[保存数据] 保存失败: {str(e)}")
            return False

    def load_from_json(self, file_path: str = "data/books.json") -> bool:
        """
        从JSON文件加载书籍列表
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否加载成功
        """
        try:
            if not os.path.exists(file_path):
                if self.logger:
                    self.logger.warning(f"[加载数据] 文件不存在: {file_path}")
                return False
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.base_url = data.get('base_url')
            self.token = data.get('token')
            
            self.books = []
            for book_data in data.get('books', []):
                book = BookInfo.from_dict(book_data)
                self.books.append(book)
            
            timer_book_ids = data.get('timer_book_ids', [])
            if timer_book_ids:
                auto_sync = data.get('auto_sync', self.config.auto_sync)
                self.start_sync_timer(interval_hours=auto_sync)
                for book_id in timer_book_ids:
                    book = self.get_book_by_id(book_id)
                    if book:
                        self.add_book_to_timer(book)
            
            if self.logger:
                self.logger.info(f"[加载数据] 加载成功: {file_path}, 书籍数: {len(self.books)}, 定时任务书籍ID: {timer_book_ids}")
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"[加载数据] 加载失败: {str(e)}")
            return False

    def refresh_all_chapters(self) -> None:
        """
        刷新所有书籍的章节列表
        """
        for book in self.books:
            self.update_chapters(cast(BookInfo, book))

    def get_download_progress(self, book: BookInfo) -> dict:
        """
        获取书籍下载进度
        
        Args:
            book: 书籍信息
            
        Returns:
            进度信息字典
        """
        total = len(book.Chapters)
        if total == 0:
            return {"total": 0, "downloaded": 0, "progress": 0}
        
        downloaded = sum(1 for ch in book.Chapters if ch.downloaded)
        progress = int(downloaded / total * 100)
        
        return {
            "total": total,
            "downloaded": downloaded,
            "progress": progress
        }

    def start_download(self, book: BookInfo) -> None:
        """
        开始下载书籍的所有未下载章节
        
        Args:
            book: 书籍信息
        """
        undownloaded = self.get_undownloaded_chapters(book)
        if not undownloaded:
            if self.logger:
                self.logger.info(f"[下载管理] 书籍无可下载章节: {book.Title}")
            return
        
        if self._download_manager is None:
            if not self.base_url:
                if self.logger:
                    self.logger.error(f"[下载管理] BaseURL未初始化")
                return
            
            self._download_manager = DownloadManager(
                config=self.config.to_dict(),
                logger=self.logger,
                base_url=self.base_url,
                on_complete=self._on_download_complete
            )
        
        self._download_manager.add_tasks(undownloaded)
        self._download_manager.start()
        
        if self.logger:
            self.logger.info(f"[下载管理] 开始下载: {book.Title}, 章节数: {len(undownloaded)}")

    def sync_and_download(self, book: BookInfo) -> bool:
        """
        一条龙服务：更新章节 -> 获取未下载章节 -> 添加下载任务
        
        Args:
            book: 书籍信息
            
        Returns:
            是否成功启动下载
        """
        if self.logger:
            self.logger.info(f"[下载管理] 开始同步: {book.Title}")
        
        chapters = self.update_chapters(book)
        if chapters is False:
            if self.logger:
                self.logger.error(f"[下载管理] 同步失败: {book.Title}")
            return False
        
        undownloaded = self.get_undownloaded_chapters(book)
        if not undownloaded:
            if self.logger:
                self.logger.info(f"[下载管理] 暂无未下载章节: {book.Title}")
            return True
        
        self.start_download(book)
        return True

    def pause_download(self) -> None:
        """暂停下载"""
        if self._download_manager:
            self._download_manager.pause()

    def resume_download(self) -> None:
        """恢复下载"""
        if self._download_manager:
            self._download_manager.resume()

    def cancel_download(self) -> None:
        """取消下载"""
        if self._download_manager:
            self._download_manager.cancel()

    def wait_download(self) -> None:
        """等待下载完成"""
        if self._download_manager:
            self._download_manager.wait()

    def start_sync_timer(self, interval_hours: Optional[float] = None) -> None:
        """
        启动定时同步任务
        
        Args:
            interval_hours: 同步间隔（小时），如果不传则从 config 读取
        """
        if self._sync_timer and self._sync_timer._is_running:
            if self.logger:
                self.logger.warning(f"[定时任务] 定时器已在运行")
            return
        
        existing_book_ids = []
        if self._sync_timer:
            existing_book_ids = self._sync_timer.get_book_ids()
            self._sync_timer.stop()
        
        if interval_hours is None:
            interval_hours = self.config.auto_sync
        
        self._sync_timer = SyncTimer(
            interval_hours=interval_hours,
            sync_func=self.sync_and_download,
            logger=self.logger
        )
        self._sync_timer.set_book_provider(self.get_book_by_id)
        
        for book_id in existing_book_ids:
            book = self.get_book_by_id(book_id)
            if book:
                self._sync_timer.add_book(book)
        
        self._sync_timer.start()

    def stop_sync_timer(self) -> None:
        """停止定时同步任务"""
        if self._sync_timer:
            self._sync_timer.stop()

    def add_book_to_timer(self, book: BookInfo) -> bool:
        """
        向定时任务添加书籍
        
        Args:
            book: 书籍信息
            
        Returns:
            是否添加成功
        """
        if not self._sync_timer:
            if self.logger:
                self.logger.warning(f"[定时任务] 定时器未启动，请先调用 start_sync_timer")
            return False
        self._sync_timer.add_book(book)
        return True

    def remove_book_from_timer(self, book: BookInfo) -> bool:
        """
        从定时任务移除书籍
        
        Args:
            book: 书籍信息
            
        Returns:
            是否移除成功
        """
        if not self._sync_timer:
            if self.logger:
                self.logger.warning(f"[定时任务] 定时器未启动")
            return False
        self._sync_timer.remove_book_by_id(book.id)
        return True

    def get_timer_book_ids(self) -> list:
        """
        获取定时任务中的书籍ID列表
        
        Returns:
            书籍ID列表
        """
        if self._sync_timer:
            return self._sync_timer.get_book_ids()
        return []

    def get_download_status(self) -> dict:
        """
        获取下载状态
        
        Returns:
            状态字典
        """
        if self._download_manager:
            return self._download_manager.get_status()
        return {
            "total": 0,
            "pending": 0,
            "downloading": 0,
            "paused": 0,
            "completed": 0,
            "failed": 0,
            "is_running": False,
            "is_paused": False
        }

    def _on_download_complete(self, chapter: ChapterInfo, success: bool) -> None:
        """
        下载完成回调
        
        Args:
            chapter: 章节信息
            success: 是否下载成功
        """
        self.set_chapter_downloaded(chapter, success)

    def get_config(self) -> dict:
        """
        获取当前配置
        
        Returns:
            配置字典
        """
        return self.config.to_dict()

    def set_config(self, key: str, value: Any) -> bool:
        """
        设置配置项
        
        Args:
            key: 配置键名
            value: 配置值
            
        Returns:
            是否设置成功
        """
        try:
            self.config.set(key, value)
            self.config.save()
            if self.logger:
                self.logger.info(f"[配置管理] 设置配置成功: {key} = {value}")
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"[配置管理] 设置配置失败: {str(e)}")
            return False

    def save_config(self) -> bool:
        """
        保存配置到文件
        
        Returns:
            是否保存成功
        """
        try:
            self.config.save()
            if self.logger:
                self.logger.info(f"[配置管理] 保存配置成功")
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"[配置管理] 保存配置失败: {str(e)}")
            return False
