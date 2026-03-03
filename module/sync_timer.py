"""
定时任务模块 - 定时执行同步下载任务
"""
import threading
import time
from typing import Callable, Optional, List, Union

from module.data_provider import BookInfo
from module.config import Config


class SyncTimer:
    """
    定时同步任务器
    
    每隔指定小时数执行 sync_and_download
    存储 BookID，定时运行时从 manager 获取最新的 BookInfo
    """

    def __init__(self, config: Union[Config, float], sync_func: Callable[[BookInfo], bool], logger=None):
        """
        初始化定时器
        
        Args:
            config: Config 对象或同步间隔（小时）
            sync_func: 同步函数，签名为 sync_func(book: BookInfo) -> bool
            logger: 日志记录器
        """
        self._config = config
        self._sync_func = sync_func
        self.logger = logger
        
        self._book_ids: List[int] = []
        self._get_book_func: Optional[Callable[[int], Optional[BookInfo]]] = None
        self._lock = threading.Lock()
        
        self._is_running = False
        self._timer_thread: Optional[threading.Thread] = None
        
        self._refresh_interval()

    def _refresh_interval(self) -> None:
        """从配置刷新间隔时间"""
        if isinstance(self._config, Config):
            self.interval_hours = self._config.auto_sync
        else:
            self.interval_hours = float(self._config)
        self.interval_seconds = self.interval_hours * 3600

    def set_book_provider(self, get_book_func: Callable[[int], Optional[BookInfo]]) -> None:
        """
        设置书籍提供者函数
        
        Args:
            get_book_func: 根据 book_id 获取 BookInfo 的函数
        """
        self._get_book_func = get_book_func

    def add_book(self, book: BookInfo) -> None:
        """
        添加书籍到定时任务（存储 BookID）
        
        Args:
            book: 书籍信息
        """
        with self._lock:
            if book.id not in self._book_ids:
                self._book_ids.append(book.id)
                if self.logger:
                    self.logger.info(f"[定时任务] 添加书籍ID: {book.id}, 标题: {book.Title}")

    def remove_book_by_id(self, book_id: int) -> None:
        """
        从定时任务移除书籍（根据 BookID）
        
        Args:
            book_id: 书籍ID
        """
        with self._lock:
            if book_id in self._book_ids:
                self._book_ids.remove(book_id)
                if self.logger:
                    self.logger.info(f"[定时任务] 移除书籍ID: {book_id}")

    def get_book_ids(self) -> List[int]:
        """
        获取定时任务中的书籍ID列表
        
        Returns:
            书籍ID列表副本
        """
        with self._lock:
            return self._book_ids.copy()

    def start(self) -> None:
        """
        启动定时任务
        """
        if self._is_running:
            if self.logger:
                self.logger.warning(f"[定时任务] 定时器已在运行")
            return
        
        self._refresh_interval()
        
        self._is_running = True
        self._timer_thread = threading.Thread(target=self._run, daemon=True, name="SyncTimer")
        self._timer_thread.start()
        
        if self.logger:
            self.logger.info(f"[定时任务] 启动定时器, 间隔: {self.interval_hours}小时")

    def stop(self) -> None:
        """
        停止定时任务
        """
        self._is_running = False
        
        if self._timer_thread:
            self._timer_thread.join(timeout=2)
            self._timer_thread = None
        
        if self.logger:
            self.logger.info(f"[定时任务] 停止定时器")

    def _run(self) -> None:
        """定时任务主循环"""
        self._refresh_interval()
        
        if self.logger:
            self.logger.info(f"[定时任务] 等待 {self.interval_hours} 小时后开始第一次同步")
        
        while self._is_running:
            time.sleep(self.interval_seconds)
            
            if not self._is_running:
                break
            
            self._refresh_interval()
            
            if self.logger:
                self.logger.info(f"[定时任务] 开始执行同步任务")
            
            with self._lock:
                book_ids_copy = self._book_ids.copy()
            
            for book_id in book_ids_copy:
                if not self._is_running:
                    break
                
                book = None
                if self._get_book_func:
                    book = self._get_book_func(book_id)
                
                if book is None:
                    if self.logger:
                        self.logger.warning(f"[定时任务] 书籍ID {book_id} 不存在，已从定时任务移除")
                    self.remove_book_by_id(book_id)
                    continue
                
                try:
                    self._sync_func(book)
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"[定时任务] 同步失败: {book.Title}, 错误: {e}")
            
            if self.logger:
                self.logger.info(f"[定时任务] 本次同步完成, 等待 {self.interval_hours} 小时")
