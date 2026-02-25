import os
import re
import json
import time
import queue
import socket
import ssl
import threading
from urllib.parse import urlparse
from urllib.request import build_opener, Request
from urllib.error import URLError
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from config import Config
from logger import get_logger

logger = get_logger(__name__)


@dataclass
class AudioInfo:
    name: str
    artist: str
    url: str
    album: str = ""
    file_path: str = ""
    download_status: str = "pending"
    retry_count: int = 0
    error_message: str = ""
    list_id: int = 0
    
    def generate_file_path(self, base_dir: str = ""):
        logger.debug(f"[AudioInfo] generate_file_path called for name={self.name}")
        safe_album = self.sanitize_filename(self.album or "未知专辑")
        safe_artist = self.sanitize_filename(self.artist or "未知艺术家")
        safe_name = self.sanitize_filename(self.name or "未知音频")
        extension = self.get_file_extension()
        
        folder_name = f"{safe_album} - {safe_artist}"
        
        if base_dir:
            album_dir = os.path.join(base_dir, folder_name)
            os.makedirs(album_dir, exist_ok=True)
            self.file_path = os.path.join(album_dir, f"{safe_name}.{extension}")
        else:
            self.file_path = os.path.join(folder_name, f"{safe_name}.{extension}")
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        logger.debug(f"[AudioInfo] sanitize_filename called for {filename}")
        illegal_chars = r'[<>:"/\\|?*\x00-\x1F]'
        safe_name = re.sub(illegal_chars, '_', filename)
        safe_name = re.sub(r'_+', '_', safe_name)
        if len(safe_name) > 200:
            safe_name = safe_name[:200]
        return safe_name.strip()
    
    def get_file_extension(self) -> str:
        logger.debug(f"[AudioInfo] get_file_extension called")
        parsed_url = urlparse(self.url)
        path = parsed_url.path
        
        if '.' in path:
            extension = path.split('.')[-1].split('?')[0].split('#')[0]
            if len(extension) > 10:
                extension = extension[:10]
            return extension.lower()
        return 'mp3'


class DownloadWorker(threading.Thread):
    def __init__(self, work_queue: queue.Queue, result_queue: queue.Queue, 
                 max_retries: int = 3, timeout: int = 60):
        logger.debug(f"[DownloadWorker] __init__ called with max_retries={max_retries}, timeout={timeout}")
        super().__init__()
        self.work_queue = work_queue
        self.result_queue = result_queue
        self.max_retries = max_retries
        self.timeout = timeout
        self.daemon = True
        self._stop_event = threading.Event()
        
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        self.opener = build_opener()
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
    
    def stop(self):
        logger.debug(f"[DownloadWorker] stop called")
        self._stop_event.set()
    
    def run(self):
        logger.debug(f"[DownloadWorker] run called")
        while not self._stop_event.is_set():
            try:
                audio_info = self.work_queue.get(timeout=1)
                if audio_info is None:
                    break
                
                audio_info.download_status = "downloading"
                success = self.download_with_retry(audio_info)
                if audio_info.download_status != "expired":
                    audio_info.download_status = "success" if success else "failed"
                
                self.result_queue.put(audio_info)
                self.work_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                if audio_info:
                    audio_info.download_status = "failed"
                    audio_info.error_message = str(e)
                    self.result_queue.put(audio_info)
                    self.work_queue.task_done()
                continue
    
    def download_with_retry(self, audio_info: AudioInfo) -> bool:
        logger.debug(f"[DownloadWorker] download_with_retry called for {audio_info.name}")
        for attempt in range(self.max_retries):
            try:
                if self.download_file(audio_info):
                    return True
            except Exception as e:
                error_str = str(e)
                if '403' in error_str or 'HTTP Error 403' in error_str:
                    audio_info.retry_count = attempt + 1
                    audio_info.error_message = "链接已过期(403)"
                    audio_info.download_status = "expired"
                    logger.warning(f"链接过期，跳过重试: {audio_info.url}")
                    return False
                
                audio_info.retry_count = attempt + 1
                audio_info.error_message = f"尝试 {attempt + 1}/{self.max_retries} 失败: {e}"
                
                if attempt < self.max_retries - 1:
                    wait_time = self.config.REQUEST_INTERVAL
                    time.sleep(wait_time)
        
        return False
    
    def _download_core(self, audio_info: AudioInfo, timeout: int,
                       headers: Dict, opener,
                       progress_callback=None,
                       stop_check_callback=None,
                       verify_size: bool = True) -> bool:
        logger.debug(f"[DownloadWorker] _download_core called for {audio_info.name}")
        if os.path.exists(audio_info.file_path):
            file_size = os.path.getsize(audio_info.file_path)
            if file_size > 1024:
                logger.info(f"文件已存在，跳过: {audio_info.file_path}")
                return True
            else:
                os.remove(audio_info.file_path)

        request = Request(audio_info.url, headers=headers)
        socket.setdefaulttimeout(timeout)

        response = opener.open(request)

        file_size = 0
        if 'content-length' in response.headers:
            file_size = int(response.headers['content-length'])

        downloaded = 0
        chunk_size = 8192

        with open(audio_info.file_path, 'wb') as f:
            while True:
                if stop_check_callback and stop_check_callback():
                    f.close()
                    if os.path.exists(audio_info.file_path):
                        os.remove(audio_info.file_path)
                    return False

                chunk = response.read(chunk_size)
                if not chunk:
                    break

                f.write(chunk)
                downloaded += len(chunk)

                if progress_callback and file_size > 0 and downloaded % (chunk_size * 100) == 0:
                    progress_callback(downloaded, file_size, audio_info.name)

        if verify_size and file_size > 0:
            actual_size = os.path.getsize(audio_info.file_path)
            if actual_size < file_size * 0.9:
                raise ValueError(f"文件大小不完整: {actual_size}/{file_size}")

        return True

    def download_file(self, audio_info: AudioInfo) -> bool:
        logger.debug(f"[DownloadWorker] download_file called for {audio_info.name}")
        def progress_callback(downloaded: int, total_size: int, name: str):
            percent = (downloaded / total_size) * 100
            short_name = name[:30] + "..." if len(name) > 30 else name
            logger.debug(f"  {short_name}: {percent:.1f}%")

        def stop_check_callback():
            return self._stop_event.is_set()

        try:
            return self._download_core(
                audio_info=audio_info,
                timeout=self.timeout,
                headers=self.headers,
                opener=self.opener,
                progress_callback=progress_callback,
                stop_check_callback=stop_check_callback,
                verify_size=True
            )
        except (URLError, socket.timeout, ConnectionError) as e:
            if os.path.exists(audio_info.file_path):
                try:
                    os.remove(audio_info.file_path)
                except:
                    pass
            raise e


class AudioDownloader:
    def __init__(self, max_workers: int = None, max_retries: int = None, download_dir: str = None):
        logger.debug(f"[AudioDownloader] __init__ called with max_workers={max_workers}, max_retries={max_retries}, download_dir={download_dir}")
        self.config = Config()
        self.max_workers = max_workers or self.config.MAX_WORKERS
        self.max_retries = max_retries or self.config.MAX_RETRIES
        self.download_dir = download_dir or self.config.DEFAULT_DOWNLOAD_DIR
        self.work_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.workers = []
        self.total_files = 0
        self.completed_files = 0
        self.failed_files = 0
        self.progress_lock = threading.Lock()
    
    def load_from_json(self, json_file: str = None) -> List[AudioInfo]:
        logger.debug(f"[AudioDownloader] load_from_json called with json_file={json_file}")
        json_file = json_file or self.config.JSON_OUTPUT_FILE
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            audio_infos = []
            
            if isinstance(data, list):
                for item in data:
                    audio_info = AudioInfo(
                        name=item.get('name', '未知名称'),
                        artist=item.get('artist', '未知艺术家'),
                        url=item.get('url', ''),
                        album=item.get('album_name', '')
                    )
                    audio_infos.append(audio_info)
            elif isinstance(data, dict) and 'audio_list' in data:
                for item in data['audio_list']:
                    audio_info = AudioInfo(
                        name=item.get('name', '未知名称'),
                        artist=item.get('artist', '未知艺术家'),
                        url=item.get('url', ''),
                        album=item.get('album_name', '')
                    )
                    audio_infos.append(audio_info)
            else:
                raise ValueError("JSON格式不支持")
            
            logger.info(f"从 {json_file} 加载了 {len(audio_infos)} 个音频信息")
            return audio_infos
            
        except FileNotFoundError:
            logger.error(f"错误: 文件不存在 - {json_file}")
            return []
        except json.JSONDecodeError:
            logger.error(f"错误: JSON格式错误 - {json_file}")
            return []
        except Exception as e:
            logger.error(f"错误: 加载JSON文件失败 - {e}")
            return []
    
    def prepare_tasks(self, audio_infos: List[AudioInfo]):
        logger.debug(f"[AudioDownloader] prepare_tasks called with {len(audio_infos)} items")
        self.total_files = len(audio_infos)
        
        for audio_info in audio_infos:
            audio_info.generate_file_path(self.download_dir)
            
            if os.path.exists(audio_info.file_path):
                file_size = os.path.getsize(audio_info.file_path)
                if file_size > 1024:
                    audio_info.download_status = "success"
                    self.result_queue.put(audio_info)
                    self.completed_files += 1
                    continue
            
            self.work_queue.put(audio_info)
    
    def start_workers(self):
        logger.debug(f"[AudioDownloader] start_workers called")
        logger.info(f"启动 {self.max_workers} 个工作线程...")
        
        for i in range(self.max_workers):
            worker = DownloadWorker(
                work_queue=self.work_queue,
                result_queue=self.result_queue,
                max_retries=self.max_retries,
                timeout=self.config.DOWNLOAD_TIMEOUT
            )
            worker.start()
            self.workers.append(worker)
    
    def monitor_progress(self):
        logger.debug(f"[AudioDownloader] monitor_progress called")
        logger.info(f"开始下载 {self.total_files} 个音频文件...")
        logger.debug("=" * 60)
        
        start_time = time.time()
        
        while self.completed_files + self.failed_files < self.total_files:
            try:
                audio_info = self.result_queue.get(timeout=1)
                
                with self.progress_lock:
                    if audio_info.download_status == "success":
                        self.completed_files += 1
                        status = "✓ 成功"
                    elif audio_info.download_status == "expired":
                        self.failed_files += 1
                        status = "⚠ 链接过期"
                    else:
                        self.failed_files += 1
                        status = f"✗ 失败 (重试 {audio_info.retry_count} 次)"
                    
                    elapsed = time.time() - start_time
                    progress = (self.completed_files + self.failed_files) / self.total_files * 100
                    
                    short_name = audio_info.name[:40] + "..." if len(audio_info.name) > 40 else audio_info.name
                    logger.info(f"{status}: {short_name}")
                    
                    if (self.completed_files + self.failed_files) % 10 == 0 or \
                       (self.completed_files + self.failed_files) == self.total_files:
                        self.print_summary(elapsed)
                
                self.result_queue.task_done()
                
            except queue.Empty:
                continue
        
        total_elapsed = time.time() - start_time
        self.print_summary(total_elapsed, final=True)
    
    def print_summary(self, elapsed_time: float, final: bool = False):
        logger.debug(f"[AudioDownloader] print_summary called with elapsed_time={elapsed_time}, final={final}")
        completed = self.completed_files
        failed = self.failed_files
        total = self.total_files
        
        if final:
            logger.info("下载完成!")
        
        logger.info(f"进度: {completed + failed}/{total} | 成功: {completed} | 失败: {failed} | 用时: {elapsed_time:.1f}秒")
        
        if completed + failed > 0:
            avg_time = elapsed_time / (completed + failed)
            logger.debug(f"平均每个文件: {avg_time:.1f}秒")
    
    def download(self, json_file: str = None) -> bool:
        logger.debug(f"[AudioDownloader] download called with json_file={json_file}")
        audio_infos = self.load_from_json(json_file)
        if not audio_infos:
            logger.warning("没有可下载的音频信息")
            return False
        
        self.prepare_tasks(audio_infos)
        self.start_workers()
        self.monitor_progress()
        
        self.work_queue.join()
        self.result_queue.join()
        
        for worker in self.workers:
            worker.stop()
        
        for worker in self.workers:
            worker.join(timeout=2)
        
        success_rate = self.completed_files / self.total_files * 100 if self.total_files > 0 else 0
        logger.info(f"最终结果: {self.completed_files}/{self.total_files} 成功 ({success_rate:.1f}%)")
        
        self.save_results(audio_infos)
        
        return self.completed_files > 0
    
    def download_with_callback(self, audio_infos: List[AudioInfo], progress_callback=None) -> bool:
        logger.debug(f"[AudioDownloader] download_with_callback called with {len(audio_infos)} items")
        if not audio_infos:
            logger.warning("没有可下载的音频信息")
            return False
        
        self.completed_files = 0
        self.failed_files = 0
        
        self.prepare_tasks(audio_infos)
        
        if progress_callback:
            progress_callback("started", "")
        
        self.start_workers()
        
        start_time = time.time()
        while self.completed_files + self.failed_files < self.total_files:
            try:
                audio_info = self.result_queue.get(timeout=1)
                
                with self.progress_lock:
                    if audio_info.download_status == "success":
                        self.completed_files += 1
                        status = "✓ 成功"
                    elif audio_info.download_status == "expired":
                        self.failed_files += 1
                        status = "⚠ 链接过期"
                    else:
                        self.failed_files += 1
                        status = f"✗ 失败"
                    
                    if progress_callback:
                        if audio_info.download_status == "success":
                            progress_callback("success", audio_info.name)
                        elif audio_info.download_status == "expired":
                            progress_callback("expired", audio_info.name)
                        else:
                            progress_callback("failed", audio_info.name)
                    
                    logger.info(f"{status}: {audio_info.name}")
                
                self.result_queue.task_done()
                
            except queue.Empty:
                continue
        
        for worker in self.workers:
            worker.stop()
        
        for worker in self.workers:
            worker.join(timeout=2)
        
        return self.completed_files > 0
    
    def save_results(self, audio_infos: List[AudioInfo]):
        logger.debug(f"[AudioDownloader] save_results called with {len(audio_infos)} items")
        results_file = os.path.join(self.download_dir, "download_results.txt")
        
        try:
            with open(results_file, 'w', encoding='utf-8') as f:
                f.write(f"下载结果 - {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 60 + "\n")
                
                for audio_info in audio_infos:
                    if audio_info.download_status == "success":
                        status = "成功"
                    elif audio_info.download_status == "expired":
                        status = "链接过期"
                    else:
                        status = "失败"
                    f.write(f"名称: {audio_info.name}\n")
                    f.write(f"艺术家: {audio_info.artist}\n")
                    f.write(f"状态: {status}\n")
                    f.write(f"重试次数: {audio_info.retry_count}\n")
                    if audio_info.error_message:
                        f.write(f"错误信息: {audio_info.error_message}\n")
                    f.write(f"保存路径: {audio_info.file_path}\n")
                    f.write("-" * 40 + "\n")
            
            logger.info(f"下载结果已保存到: {results_file}")
            
        except Exception as e:
            logger.error(f"保存下载结果失败: {e}")

    @staticmethod
    def _download_core_static(audio_info: AudioInfo, timeout: int,
                              headers: Dict, opener,
                              verify_size: bool = False) -> bool:
        logger.debug(f"[AudioDownloader] _download_core_static called for {audio_info.name}")
        if os.path.exists(audio_info.file_path):
            file_size = os.path.getsize(audio_info.file_path)
            if file_size > 1024:
                logger.info(f"文件已存在，跳过: {audio_info.file_path}")
                return True
            else:
                try:
                    os.remove(audio_info.file_path)
                except:
                    pass

        request = Request(audio_info.url, headers=headers)
        socket.setdefaulttimeout(timeout)

        try:
            response = opener.open(request)

            file_size = 0
            if 'content-length' in response.headers:
                file_size = int(response.headers['content-length'])

            downloaded = 0
            chunk_size = 8192

            with open(audio_info.file_path, 'wb') as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)

            if verify_size and file_size > 0:
                actual_size = os.path.getsize(audio_info.file_path)
                if actual_size < file_size * 0.9:
                    raise ValueError(f"文件大小不完整: {actual_size}/{file_size}")

            logger.info(f"下载成功 - 名称: {audio_info.name} | 路径: {audio_info.file_path} | 大小: {downloaded} bytes")
            return True

        except Exception as e:
            logger.error(f"下载失败 - 名称: {audio_info.name} | 链接: {audio_info.url} | 错误: {e}")
            if os.path.exists(audio_info.file_path):
                try:
                    os.remove(audio_info.file_path)
                except:
                    pass
            audio_info.error_message = str(e)
            return False