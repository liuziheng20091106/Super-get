"""
FastAPI 服务 - 为 Vue 前端提供 REST API
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Any
from contextlib import asynccontextmanager

from module.data_provider import SearchResult
from module.download_manager import DownloadManager
from module.manager import Manager


class ManagerHolder:
    """Manager 实例持有者"""
    manager: Optional[Manager] = None


holder = ManagerHolder()


def get_manager() -> Manager:
    """获取 Manager 实例，如果未初始化则抛出错误"""
    if holder.manager is None:
        raise RuntimeError("Manager 未初始化")
    return holder.manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    manager = get_manager()
    manager.save_to_json()
    manager.cancel_download()
    manager.stop_sync_timer()


def create_app(manager: Manager) -> FastAPI:
    """创建 FastAPI 应用"""
    holder.manager = manager

    app = FastAPI(title="365听书 API", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def root():
        return {"message": "365听书 API"}

    @app.get("/api/search")
    async def search(q: str = ""):
        if not q:
            return []
        mgr = get_manager()
        results = mgr.search_books(q)
        if results is False or not isinstance(results, list):
            return {"error": "搜索失败"}
        return [{
            "id": r.id,
            "bookTitle": r.bookTitle,
            "bookDesc": r.bookDesc,
            "bookImage": r.bookImage,
            "bookAnchor": r.bookAnchor,
            "count": r.count,
            "updateStatus": r.UpdateStatus,
            "heat": r.heat
        } for r in results]

    @app.get("/api/books")
    async def get_books():
        mgr = get_manager()
        books = mgr.get_books()
        return [{
            "id": b.id,
            "count": b.count,
            "updateStatus": b.UpdateStatus,
            "image": b.Image,
            "desc": b.Desc,
            "title": b.Title,
            "anchor": b.Anchor
        } for b in books]

    class AddBookRequest(BaseModel):
        id: int

    @app.post("/api/book/add")
    async def add_book(req: AddBookRequest):
        mgr = get_manager()
        for book in mgr.get_books():
            if book.id == req.id:
                return {"message": "书籍已存在"}

        sr = SearchResult(
            id=req.id,
            bookTitle="",
            bookDesc="",
            bookImage="",
            bookAnchor="",
            count=0,
            UpdateStatus=0,
            heat=0
        )

        success = mgr.add_book(sr)
        if success:
            mgr.save_to_json()
            return {"message": "添加成功"}
        return {"error": "添加失败"}

    @app.delete("/api/book/{book_id}")
    async def delete_book(book_id: int):
        mgr = get_manager()
        book = mgr.get_book_by_id(book_id)
        if not book:
            raise HTTPException(status_code=404, detail="书籍不存在")
        mgr.remove_book(book)
        mgr.save_to_json()
        return {"message": "删除成功"}

    @app.get("/api/book/{book_id}")
    async def get_book(book_id: int):
        mgr = get_manager()
        book = mgr.get_book_by_id(book_id)
        if not book:
            raise HTTPException(status_code=404, detail="书籍不存在")

        downloaded_count = mgr.len_downloaded_chapters(book)
        total = len(book.Chapters)
        progress = int(downloaded_count / total * 100) if total > 0 else 0

        return {
            "id": book.id,
            "count": book.count,
            "updateStatus": book.UpdateStatus,
            "image": book.Image,
            "desc": book.Desc,
            "title": book.Title,
            "anchor": book.Anchor,
            "downloaded": downloaded_count,
            "progress": progress
        }

    @app.get("/api/book/{book_id}/chapters")
    async def get_chapters(book_id: int):
        mgr = get_manager()
        book = mgr.get_book_by_id(book_id)
        if not book:
            raise HTTPException(status_code=404, detail="书籍不存在")
        return [{
            "chapterid": c.chapterid,
            "position": c.position,
            "title": c.title,
            "downloaded": c.downloaded
        } for c in book.Chapters]

    @app.post("/api/book/{book_id}/chapters")
    async def update_chapters(book_id: int):
        mgr = get_manager()
        book = mgr.get_book_by_id(book_id)
        if not book:
            raise HTTPException(status_code=404, detail="书籍不存在")
        mgr.update_chapters(book)
        mgr.save_to_json()
        return {"message": f"章节已更新"}

    class DownloadRequest(BaseModel):
        book_id: Optional[int] = None
        chapter_ids: Optional[List[int]] = None

    @app.post("/api/download/start")
    async def download_start(req: Optional[DownloadRequest] = None):
        mgr = get_manager()
        if req and req.book_id:
            book = mgr.get_book_by_id(req.book_id)
            if not book:
                raise HTTPException(status_code=404, detail="书籍不存在")

            if req.chapter_ids:
                if not book.Chapters:
                    raise HTTPException(status_code=400, detail="书籍暂无章节")
                chapters = [c for c in book.Chapters if c.chapterid in req.chapter_ids and not c.downloaded]
                if not chapters:
                    raise HTTPException(status_code=400, detail="没有未下载的章节")
            else:
                if not book.Chapters:
                    raise HTTPException(status_code=400, detail="书籍暂无章节")
                chapters = [c for c in book.Chapters if not c.downloaded]
                if not chapters:
                    raise HTTPException(status_code=400, detail="没有未下载的章节")

            if mgr._download_manager is None:
                base_url = mgr.base_url
                if not base_url:
                    raise HTTPException(status_code=500, detail="BaseURL未配置")
                mgr._download_manager = DownloadManager(
                    config=mgr.config,
                    logger=mgr.logger,
                    base_url=base_url,
                    on_complete=mgr._on_download_complete
                )

            count = mgr._download_manager.add_tasks(chapters)
            mgr._download_manager.start()
            return {"message": f"添加了 {count} 个下载任务"}
        else:
            total_count = 0
            for book in mgr.get_books():
                undownloaded = [c for c in book.Chapters if not c.downloaded]
                if undownloaded:
                    if mgr._download_manager is None:
                        base_url = mgr.base_url
                        if not base_url:
                            raise HTTPException(status_code=500, detail="BaseURL未配置")
                        mgr._download_manager = DownloadManager(
                            config=mgr.config,
                            logger=mgr.logger,
                            base_url=base_url,
                            on_complete=mgr._on_download_complete
                        )
                    count = mgr._download_manager.add_tasks(undownloaded)
                    total_count += count

            if total_count == 0:
                return {"message": "没有未下载的章节"}

            if mgr._download_manager:
                mgr._download_manager.start()
            return {"message": f"添加了 {total_count} 个下载任务"}

    @app.post("/api/download/pause")
    async def download_pause(req: Optional[DownloadRequest] = None):
        mgr = get_manager()
        if not mgr._download_manager:
            return {"message": "没有正在进行的下载"}

        if req and req.book_id:
            book = mgr.get_book_by_id(req.book_id)
            if not book:
                raise HTTPException(status_code=404, detail="书籍不存在")

        mgr.pause_download()
        return {"message": "已暂停"}

    @app.post("/api/download/resume")
    async def download_resume(req: Optional[DownloadRequest] = None):
        mgr = get_manager()
        if not mgr._download_manager:
            return {"message": "没有正在进行的下载"}

        if req and req.book_id:
            book = mgr.get_book_by_id(req.book_id)
            if not book:
                raise HTTPException(status_code=404, detail="书籍不存在")

        mgr.resume_download()
        return {"message": "已继续"}

    @app.post("/api/download/cancel")
    async def download_cancel(req: Optional[DownloadRequest] = None):
        mgr = get_manager()
        if not mgr._download_manager:
            return {"message": "没有正在进行的下载"}

        if req and req.book_id:
            book = mgr.get_book_by_id(req.book_id)
            if not book:
                raise HTTPException(status_code=404, detail="书籍不存在")

        mgr.cancel_download()
        return {"message": "已取消"}

    @app.get("/api/download/status")
    async def download_status():
        mgr = get_manager()
        return mgr.get_download_status()

    class TimerRequest(BaseModel):
        interval_hours: Optional[float] = None

    class TimerBookRequest(BaseModel):
        book_id: int

    @app.post("/api/timer/start")
    async def timer_start(req: Optional[TimerRequest] = None):
        mgr = get_manager()
        interval = req.interval_hours if req else None
        mgr.start_sync_timer(interval_hours=interval)
        return {"message": "定时任务已启动"}

    @app.post("/api/timer/stop")
    async def timer_stop():
        mgr = get_manager()
        mgr.stop_sync_timer()
        return {"message": "定时任务已停止"}

    @app.post("/api/timer/book/add")
    async def timer_add_book(req: TimerBookRequest):
        mgr = get_manager()
        book = mgr.get_book_by_id(req.book_id)
        if not book:
            raise HTTPException(status_code=404, detail="书籍不存在")

        success = mgr.add_book_to_timer(book)
        if not success:
            raise HTTPException(status_code=400, detail="定时器未启动，请先启动定时任务")

        mgr.save_to_json()
        return {"message": "已添加到定时任务"}

    @app.post("/api/timer/book/remove")
    async def timer_remove_book(req: TimerBookRequest):
        mgr = get_manager()
        book = mgr.get_book_by_id(req.book_id)
        if not book:
            raise HTTPException(status_code=404, detail="书籍不存在")

        success = mgr.remove_book_from_timer(book)
        if not success:
            raise HTTPException(status_code=400, detail="定时器未启动")

        mgr.save_to_json()
        return {"message": "已从定时任务移除"}

    @app.get("/api/timer/status")
    async def timer_status():
        mgr = get_manager()
        sync_timer = mgr._sync_timer
        is_running = sync_timer._is_running if sync_timer else False
        interval = sync_timer.interval_hours if sync_timer else mgr.config.auto_sync
        book_ids = mgr.get_timer_book_ids()
        return {
            "is_running": is_running,
            "interval_hours": interval,
            "book_ids": book_ids
        }

    @app.get("/api/config")
    async def get_config():
        mgr = get_manager()
        return mgr.get_config()

    class ConfigSetRequest(BaseModel):
        key: str
        value: Any

    @app.put("/api/config")
    async def set_config(req: ConfigSetRequest):
        mgr = get_manager()
        success = mgr.set_config(req.key, req.value)
        if success:
            return {"message": "配置已更新"}
        raise HTTPException(status_code=400, detail="配置更新失败")

    @app.post("/api/config/save")
    async def save_config():
        mgr = get_manager()
        success = mgr.save_config()
        if success:
            return {"message": "配置已保存"}
        raise HTTPException(status_code=400, detail="配置保存失败")

    return app



if __name__ == "__main__":
    print("本代码已被迁移到main.py中运行，请不要再动了")
