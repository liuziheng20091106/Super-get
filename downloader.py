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


@dataclass
class AudioInfo:
    name: str
    artist: str
    url: str
    file_path: str = ""
    download_status: str = "pending"
    retry_count: int = 0
    error_message: str = ""
    
    def __post_init__(self):
        if not self.file_path:
            self.generate_file_path()
    
    def generate_file_path(self, base_dir: str = "."):
        safe_artist = self.sanitize_filename(self.artist or "未知艺术家")
        safe_name = self.sanitize_filename(self.name or "未知音频")
        extension = self.get_file_extension()
        
        artist_dir = os.path.join(base_dir, safe_artist)
        os.makedirs(artist_dir, exist_ok=True)
        
        self.file_path = os.path.join(artist_dir, f"{safe_name}.{extension}")
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        illegal_chars = r'[<>:"/\\|?*\x00-\x1F]'
        safe_name = re.sub(illegal_chars, '_', filename)
        safe_name = re.sub(r'_+', '_', safe_name)
        if len(safe_name) > 200:
            safe_name = safe_name[:200]
        return safe_name.strip()
    
    def get_file_extension(self) -> str:
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
        self._stop_event.set()
    
    def run(self):
        while not self._stop_event.is_set():
            try:
                audio_info = self.work_queue.get(timeout=1)
                if audio_info is None:
                    break
                
                audio_info.download_status = "downloading"
                success = self.download_with_retry(audio_info)
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
        for attempt in range(self.max_retries):
            try:
                if self.download_file(audio_info):
                    return True
            except Exception as e:
                audio_info.retry_count = attempt + 1
                audio_info.error_message = f"尝试 {attempt + 1}/{self.max_retries} 失败: {e}"
                
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
        
        return False
    
    def download_file(self, audio_info: AudioInfo) -> bool:
        if os.path.exists(audio_info.file_path):
            file_size = os.path.getsize(audio_info.file_path)
            if file_size > 1024:
                print(f"文件已存在，跳过: {audio_info.file_path}")
                return True
            else:
                os.remove(audio_info.file_path)
        
        request = Request(audio_info.url, headers=self.headers)
        socket.setdefaulttimeout(self.timeout)
        
        try:
            response = self.opener.open(request)
            
            file_size = 0
            if 'content-length' in response.headers:
                file_size = int(response.headers['content-length'])
            
            downloaded = 0
            chunk_size = 8192
            
            with open(audio_info.file_path, 'wb') as f:
                while True:
                    if self._stop_event.is_set():
                        f.close()
                        if os.path.exists(audio_info.file_path):
                            os.remove(audio_info.file_path)
                        return False
                    
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    if file_size > 0 and downloaded % (chunk_size * 100) == 0:
                        percent = (downloaded / file_size) * 100
                        short_name = audio_info.name[:30] + "..." if len(audio_info.name) > 30 else audio_info.name
                        print(f"  {short_name}: {percent:.1f}%")
            
            actual_size = os.path.getsize(audio_info.file_path)
            if file_size > 0 and actual_size < file_size * 0.9:
                raise ValueError(f"文件大小不完整: {actual_size}/{file_size}")
            
            return True
            
        except (URLError, socket.timeout, ConnectionError) as e:
            if os.path.exists(audio_info.file_path):
                try:
                    os.remove(audio_info.file_path)
                except:
                    pass
            raise e


class AudioDownloader:
    def __init__(self, max_workers: int = None, max_retries: int = None, download_dir: str = None):
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
                        url=item.get('url', '')
                    )
                    audio_infos.append(audio_info)
            elif isinstance(data, dict) and 'audio_list' in data:
                for item in data['audio_list']:
                    audio_info = AudioInfo(
                        name=item.get('name', '未知名称'),
                        artist=item.get('artist', '未知艺术家'),
                        url=item.get('url', '')
                    )
                    audio_infos.append(audio_info)
            else:
                raise ValueError("JSON格式不支持")
            
            print(f"从 {json_file} 加载了 {len(audio_infos)} 个音频信息")
            return audio_infos
            
        except FileNotFoundError:
            print(f"错误: 文件不存在 - {json_file}")
            return []
        except json.JSONDecodeError:
            print(f"错误: JSON格式错误 - {json_file}")
            return []
        except Exception as e:
            print(f"错误: 加载JSON文件失败 - {e}")
            return []
    
    def prepare_tasks(self, audio_infos: List[AudioInfo]):
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
        print(f"启动 {self.max_workers} 个工作线程...")
        
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
        print(f"\n开始下载 {self.total_files} 个音频文件...")
        print("=" * 60)
        
        start_time = time.time()
        
        while self.completed_files + self.failed_files < self.total_files:
            try:
                audio_info = self.result_queue.get(timeout=1)
                
                with self.progress_lock:
                    if audio_info.download_status == "success":
                        self.completed_files += 1
                        status = "✓ 成功"
                    else:
                        self.failed_files += 1
                        status = f"✗ 失败 (重试 {audio_info.retry_count} 次)"
                    
                    elapsed = time.time() - start_time
                    progress = (self.completed_files + self.failed_files) / self.total_files * 100
                    
                    short_name = audio_info.name[:40] + "..." if len(audio_info.name) > 40 else audio_info.name
                    print(f"{status}: {short_name}")
                    
                    if (self.completed_files + self.failed_files) % 10 == 0 or \
                       (self.completed_files + self.failed_files) == self.total_files:
                        self.print_summary(elapsed)
                
                self.result_queue.task_done()
                
            except queue.Empty:
                continue
        
        total_elapsed = time.time() - start_time
        self.print_summary(total_elapsed, final=True)
    
    def print_summary(self, elapsed_time: float, final: bool = False):
        completed = self.completed_files
        failed = self.failed_files
        total = self.total_files
        
        if final:
            print("\n" + "=" * 60)
            print("下载完成!")
        
        print(f"进度: {completed + failed}/{total} | 成功: {completed} | 失败: {failed} | 用时: {elapsed_time:.1f}秒")
        
        if completed + failed > 0:
            avg_time = elapsed_time / (completed + failed)
            print(f"平均每个文件: {avg_time:.1f}秒")
    
    def download(self, json_file: str = None) -> bool:
        audio_infos = self.load_from_json(json_file)
        if not audio_infos:
            print("没有可下载的音频信息")
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
        print(f"\n最终结果: {self.completed_files}/{self.total_files} 成功 ({success_rate:.1f}%)")
        
        self.save_results(audio_infos)
        
        return self.completed_files > 0
    
    def save_results(self, audio_infos: List[AudioInfo]):
        results_file = os.path.join(self.download_dir, "download_results.txt")
        
        try:
            with open(results_file, 'w', encoding='utf-8') as f:
                f.write(f"下载结果 - {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 60 + "\n")
                
                for audio_info in audio_infos:
                    status = "成功" if audio_info.download_status == "success" else "失败"
                    f.write(f"名称: {audio_info.name}\n")
                    f.write(f"艺术家: {audio_info.artist}\n")
                    f.write(f"状态: {status}\n")
                    f.write(f"重试次数: {audio_info.retry_count}\n")
                    if audio_info.error_message:
                        f.write(f"错误信息: {audio_info.error_message}\n")
                    f.write(f"保存路径: {audio_info.file_path}\n")
                    f.write("-" * 40 + "\n")
            
            print(f"下载结果已保存到: {results_file}")
            
        except Exception as e:
            print(f"保存下载结果失败: {e}")

    def download_single(self, audio_info: AudioInfo) -> bool:
        if os.path.exists(audio_info.file_path):
            file_size = os.path.getsize(audio_info.file_path)
            if file_size > 1024:
                print(f"文件已存在，跳过: {audio_info.file_path}")
                return True
            else:
                try:
                    os.remove(audio_info.file_path)
                except:
                    pass
        
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        opener = build_opener()
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }
        
        try:
            request = Request(audio_info.url, headers=headers)
            socket.setdefaulttimeout(self.max_retries)
            
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
            
            return True
            
        except Exception as e:
            if os.path.exists(audio_info.file_path):
                try:
                    os.remove(audio_info.file_path)
                except:
                    pass
            audio_info.error_message = str(e)
            return False