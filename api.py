"""
FastAPI 服务 - 为 Vue 前端提供 REST API
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Any
from contextlib import asynccontextmanager

from module.data_provider import BookInfo, ChapterInfo, SearchResult
from module.download_manager import DownloadManager


class ManagerHolder:
    """Manager 实例持有者"""
    manager = None


holder = ManagerHolder()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    if holder.manager:
        holder.manager.save_to_json()
        holder.manager.cancel_download()
        holder.manager.stop_sync_timer()


def create_app(manager) -> FastAPI:
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
    
    # ========== 搜索 ==========
    @app.get("/api/search")
    async def search(q: str = ""):
        if not q:
            return []
        results = holder.manager.search_books(q)
        if results is False:
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
    
    # ========== 书籍管理 ==========
    @app.get("/api/books")
    async def get_books():
        books = holder.manager.get_books()
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
        for book in holder.manager.get_books():
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
        
        success = holder.manager.add_book(sr)
        if success:
            holder.manager.save_to_json()
            return {"message": "添加成功"}
        return {"error": "添加失败"}
    
    @app.delete("/api/book/{book_id}")
    async def delete_book(book_id: int):
        book = holder.manager.get_book_by_id(book_id)
        if not book:
            raise HTTPException(status_code=404, detail="书籍不存在")
        holder.manager.remove_book(book)
        holder.manager.save_to_json()
        return {"message": "删除成功"}
    
    @app.get("/api/book/{book_id}")
    async def get_book(book_id: int):
        book = holder.manager.get_book_by_id(book_id)
        if not book:
            raise HTTPException(status_code=404, detail="书籍不存在")
        
        downloaded_count = holder.manager.len_downloaded_chapters(book)
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
        book = holder.manager.get_book_by_id(book_id)
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
        book = holder.manager.get_book_by_id(book_id)
        if not book:
            raise HTTPException(status_code=404, detail="书籍不存在")
        holder.manager.update_chapters(book)
        holder.manager.save_to_json()
        return {"message": f"章节已更新"}
    
    # ========== 下载管理 ==========
    class DownloadRequest(BaseModel):
        book_id: Optional[int] = None
        chapter_ids: Optional[List[int]] = None
    
    @app.post("/api/download/start")
    async def download_start(req: DownloadRequest = None):
        if req and req.book_id:
            book = holder.manager.get_book_by_id(req.book_id)
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
            
            if holder.manager._download_manager is None:
                holder.manager._download_manager = DownloadManager(
                    config=holder.manager.config.to_dict(),
                    logger=holder.manager.logger,
                    base_url=holder.manager.base_url,
                    on_complete=holder.manager._on_download_complete
                )
            
            count = holder.manager._download_manager.add_tasks(chapters)
            holder.manager._download_manager.start()
            return {"message": f"添加了 {count} 个下载任务"}
        else:
            total_count = 0
            for book in holder.manager.get_books():
                undownloaded = [c for c in book.Chapters if not c.downloaded]
                if undownloaded:
                    if holder.manager._download_manager is None:
                        holder.manager._download_manager = DownloadManager(
                            config=holder.manager.config.to_dict(),
                            logger=holder.manager.logger,
                            base_url=holder.manager.base_url,
                            on_complete=holder.manager._on_download_complete
                        )
                    count = holder.manager._download_manager.add_tasks(undownloaded)
                    total_count += count
            
            if total_count == 0:
                return {"message": "没有未下载的章节"}
            
            holder.manager._download_manager.start()
            return {"message": f"添加了 {total_count} 个下载任务"}
    
    @app.post("/api/download/pause")
    async def download_pause(req: DownloadRequest = None):
        if not holder.manager._download_manager:
            return {"message": "没有正在进行的下载"}
        
        if req and req.book_id:
            book = holder.manager.get_book_by_id(req.book_id)
            if not book:
                raise HTTPException(status_code=404, detail="书籍不存在")
        
        holder.manager.pause_download()
        return {"message": "已暂停"}
    
    @app.post("/api/download/resume")
    async def download_resume(req: DownloadRequest = None):
        if not holder.manager._download_manager:
            return {"message": "没有正在进行的下载"}
        
        if req and req.book_id:
            book = holder.manager.get_book_by_id(req.book_id)
            if not book:
                raise HTTPException(status_code=404, detail="书籍不存在")
        
        holder.manager.resume_download()
        return {"message": "已继续"}
    
    @app.post("/api/download/cancel")
    async def download_cancel(req: DownloadRequest = None):
        if not holder.manager._download_manager:
            return {"message": "没有正在进行的下载"}
        
        if req and req.book_id:
            book = holder.manager.get_book_by_id(req.book_id)
            if not book:
                raise HTTPException(status_code=404, detail="书籍不存在")
        
        holder.manager.cancel_download()
        return {"message": "已取消"}
    
    @app.get("/api/download/status")
    async def download_status():
        return holder.manager.get_download_status()
    
    # ========== 定时任务 ==========
    class TimerRequest(BaseModel):
        interval_hours: Optional[float] = None
    
    class TimerBookRequest(BaseModel):
        book_id: int
    
    @app.post("/api/timer/start")
    async def timer_start(req: TimerRequest = None):
        interval = req.interval_hours if req else None
        holder.manager.start_sync_timer(interval_hours=interval)
        return {"message": "定时任务已启动"}
    
    @app.post("/api/timer/stop")
    async def timer_stop():
        holder.manager.stop_sync_timer()
        return {"message": "定时任务已停止"}
    
    @app.post("/api/timer/book/add")
    async def timer_add_book(req: TimerBookRequest):
        book = holder.manager.get_book_by_id(req.book_id)
        if not book:
            raise HTTPException(status_code=404, detail="书籍不存在")
        
        success = holder.manager.add_book_to_timer(book)
        if not success:
            raise HTTPException(status_code=400, detail="定时器未启动，请先启动定时任务")
        
        holder.manager.save_to_json()
        return {"message": "已添加到定时任务"}
    
    @app.post("/api/timer/book/remove")
    async def timer_remove_book(req: TimerBookRequest):
        book = holder.manager.get_book_by_id(req.book_id)
        if not book:
            raise HTTPException(status_code=404, detail="书籍不存在")
        
        success = holder.manager.remove_book_from_timer(book)
        if not success:
            raise HTTPException(status_code=400, detail="定时器未启动")
        
        holder.manager.save_to_json()
        return {"message": "已从定时任务移除"}
    
    @app.get("/api/timer/status")
    async def timer_status():
        is_running = holder.manager._sync_timer._is_running if holder.manager._sync_timer else False
        interval = holder.manager._sync_timer.interval_hours if holder.manager._sync_timer else holder.manager.config.auto_sync
        book_ids = holder.manager.get_timer_book_ids()
        return {
            "is_running": is_running,
            "interval_hours": interval,
            "book_ids": book_ids
        }
    
    # ========== 配置管理 ==========
    @app.get("/api/config")
    async def get_config():
        return holder.manager.get_config()
    
    class ConfigSetRequest(BaseModel):
        key: str
        value: Any
    
    @app.put("/api/config")
    async def set_config(req: ConfigSetRequest):
        success = holder.manager.set_config(req.key, req.value)
        if success:
            return {"message": "配置已更新"}
        raise HTTPException(status_code=400, detail="配置更新失败")
    
    @app.post("/api/config/save")
    async def save_config():
        success = holder.manager.save_config()
        if success:
            return {"message": "配置已保存"}
        raise HTTPException(status_code=400, detail="配置保存失败")
    
    return app




if __name__ == "__main__":
    print("本代码已被迁移到main.py中运行，请不要再动了")