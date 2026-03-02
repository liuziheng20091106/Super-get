"""
下载管理器 - 多线程下载调度器
支持暂停、恢复、取消操作

逻辑：每隔 request_interval 秒检查一次是否有空余线程，如果有则添加任务（一次一个）
"""
import threading
import queue
import time
from enum import Enum
from typing import Optional, Callable, Any, Union, Dict
from module.config import Config
from dataclasses import dataclass

from module.data_provider import ChapterInfo
from module.downloader import Downloader


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class DownloadTask:
    """下载任务单元"""
    chapter: ChapterInfo
    status: TaskStatus = TaskStatus.PENDING
    progress: int = 0
    error: str = ""
    retry_count: int = 0
    base_url: str = ""


class DownloadManager:
    """
    下载管理器
    
    提供多线程下载、暂停、恢复、取消功能
    逻辑：每隔 request_interval 秒检查一次是否有空余线程，如果有则添加任务
    """

    def __init__(self, config: Union[dict, Config], logger=None, base_url: str = "", on_complete: Optional[Callable] = None):
        """
        初始化下载管理器
        
        Args:
            config: 配置字典，需要包含 max_workers, request_interval, max_retries, download_timeout, default_download_dir
            logger: 日志记录器
            base_url: API基础URL
            on_complete: 下载完成回调函数，签名为 on_complete(chapter: ChapterInfo, success: bool)
        """
        self.config = config
        self.logger = logger
        self.base_url = base_url
        self.on_complete = on_complete
        
        self.max_workers = config.get('max_workers', 8)
        self.request_interval = config.get('request_interval', 0.5)
        
        self._pending_queue: list[DownloadTask] = []
        self._active_tasks: dict[int, DownloadTask] = {}
        self._tasks: list[DownloadTask] = []
        self._lock = threading.Lock()
        
        self._is_paused = threading.Event()
        self._is_paused.set()
        self._is_running = False
        self._scheduler_thread: Optional[threading.Thread] = None
        
        self._downloaded_count = 0
        self._failed_count = 0

    def add_task(self, chapter: ChapterInfo) -> bool:
        """
        添加单个下载任务
        
        Args:
            chapter: 章节信息
            
        Returns:
            是否添加成功
        """
        if chapter.downloaded:
            if self.logger:
                self.logger.info(f"[下载管理] 章节已下载，跳过: {chapter.title}")
            return False
        
        with self._lock:
            existing_ids = set(t.chapter.chapterid for t in self._tasks)
            if chapter.chapterid in existing_ids:
                if self.logger:
                    self.logger.info(f"[下载管理] 任务已存在，跳过: {chapter.title}")
                return False
            
            task = DownloadTask(chapter=chapter, base_url=self.base_url)
            self._tasks.append(task)
            self._pending_queue.append(task)
        
        if self.logger:
            self.logger.info(f"[下载管理] 添加任务: {chapter.title}")
        return True

    def add_tasks(self, chapters: list[ChapterInfo]) -> int:
        """
        批量添加下载任务
        
        Args:
            chapters: 章节信息列表
            
        Returns:
            实际添加的任务数
        """
        count = 0
        for chapter in chapters:
            if self.add_task(chapter):
                count += 1
        
        if self.logger:
            self.logger.info(f"[下载管理] 批量添加 {count}/{len(chapters)} 个任务")
        return count

    def start(self) -> None:
        """启动下载"""
        if self._is_running:
            if self.logger:
                self.logger.warning(f"[下载管理] 下载已在运行中")
            return
        
        self._is_running = True
        self._is_paused.set()
        
        self._scheduler_thread = threading.Thread(target=self._scheduler, daemon=True, name="DownloadScheduler")
        self._scheduler_thread.start()
        
        if self.logger:
            self.logger.info(f"[下载管理] 启动调度器")

    def pause(self) -> None:
        """暂停下载"""
        self._is_paused.clear()
        if self.logger:
            self.logger.info(f"[下载管理] 暂停下载")

    def resume(self) -> None:
        """恢复下载"""
        self._is_paused.set()
        if self.logger:
            self.logger.info(f"[下载管理] 恢复下载")

    def cancel(self) -> None:
        """取消所有下载任务"""
        self._is_running = False
        self._is_paused.set()
        
        with self._lock:
            self._pending_queue.clear()
            for task in list(self._active_tasks.values()):
                task.status = TaskStatus.FAILED
                task.error = "任务已取消"
            self._active_tasks.clear()
            self._tasks.clear()
        
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=1)
        
        if self.logger:
            self.logger.info(f"[下载管理] 已取消所有任务")

    def wait(self) -> None:
        """等待所有任务完成"""
        while True:
            with self._lock:
                if not self._pending_queue and not self._active_tasks:
                    break
            time.sleep(0.5)

    def get_status(self) -> dict:
        """
        获取下载状态
        
        Returns:
            状态字典
        """
        with self._lock:
            pending = len(self._pending_queue)
            downloading = len(self._active_tasks)
            completed = sum(1 for t in self._tasks if t.status == TaskStatus.COMPLETED)
            failed = sum(1 for t in self._tasks if t.status == TaskStatus.FAILED)
            paused = sum(1 for t in self._tasks if t.status == TaskStatus.PAUSED)
            total = len(self._tasks)
        
        return {
            "total": total,
            "pending": pending,
            "downloading": downloading,
            "paused": paused,
            "completed": completed,
            "failed": failed,
            "is_running": self._is_running,
            "is_paused": not self._is_paused.is_set()
        }

    def get_tasks(self) -> list[DownloadTask]:
        """获取所有任务"""
        with self._lock:
            return self._tasks.copy()

    def _scheduler(self) -> None:
        """调度器线程：每隔 request_interval 秒检查并分配任务"""
        while self._is_running:
            self._is_paused.wait()
            
            with self._lock:
                active_count = len(self._active_tasks)
            
            if active_count < self.max_workers and self._pending_queue:
                with self._lock:
                    task = self._pending_queue.pop(0)
                
                worker = threading.Thread(target=self._worker, args=(task,), daemon=True, name=f"Downloader-{task.chapter.chapterid}")
                worker.start()
                
                with self._lock:
                    self._active_tasks[task.chapter.chapterid] = task
            
            time.sleep(self.request_interval)

    def _worker(self, task: DownloadTask) -> None:
        """工作线程"""
        task.status = TaskStatus.DOWNLOADING
        
        if self.logger:
            self.logger.info(f"[下载管理] 开始下载: {task.chapter.title}")
        
        success = self._download(task)
        
        with self._lock:
            if task.chapter.chapterid in self._active_tasks:
                del self._active_tasks[task.chapter.chapterid]
            
            if success:
                task.status = TaskStatus.COMPLETED
                task.progress = 100
                self._downloaded_count += 1
            else:
                task.status = TaskStatus.FAILED
                self._failed_count += 1
        
        if self.on_complete:
            self.on_complete(task.chapter, success)

    def _download(self, task: DownloadTask) -> bool:
        """
        执行下载
        
        Args:
            task: 下载任务
            
        Returns:
            是否下载成功
        """
        downloader = Downloader(
            chapter_info=task.chapter,
            logger=self.logger,
            config=self.config,
            base_url=task.base_url
        )
        
        return downloader.download()
