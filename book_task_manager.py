import os
import json
import time
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict, field
from logger import get_logger

logger = get_logger(__name__)


@dataclass
class BookTask:
    album_id: int
    album_name: str
    album_artist: str
    list_id: int
    name: str
    url: str
    is_parsed: bool = False
    is_downloaded: bool = False
    audio_url: str = ""
    added_time: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))
    parsed_time: str = ""
    downloaded_time: str = ""

    def to_dict(self) -> Dict:
        #logger.debug(f"[BookTask] to_dict called for list_id={self.list_id}")
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'BookTask':
        #logger.debug(f"[BookTask] from_dict called")
        if 'audio_url' not in data:
            data['audio_url'] = ''
        return cls(**data)


class BookTaskManager:
    CONFIG_DIR = "config"
    TASKS_FILE = "tasks.json"
    CONFIG_VERSION = "1.0"

    def __init__(self):
        self.tasks: Dict[int, BookTask] = {}
        self.occupied_tasks: set = set()
        self._ensure_config_dir()

    def _ensure_config_dir(self):
        logger.debug(f"[BookTaskManager] _ensure_config_dir called")
        config_path = os.path.join(os.path.dirname(__file__), self.CONFIG_DIR)
        if not os.path.exists(config_path):
            os.makedirs(config_path)

    def _get_tasks_file_path(self) -> str:
        logger.debug(f"[BookTaskManager] _get_tasks_file_path called")
        return os.path.join(os.path.dirname(__file__), self.CONFIG_DIR, self.TASKS_FILE)

    def _get_book_config_path(self, book_id: int) -> str:
        logger.debug(f"[BookTaskManager] _get_book_config_path called with book_id={book_id}")
        return os.path.join(os.path.dirname(__file__), self.CONFIG_DIR, f"book_{book_id}.json")

    def add_task(self, album_id: int, album_name: str, album_artist: str, 
                 list_id: int, name: str, url: str, 
                 audio_url: str = "", is_parsed: bool = False) -> bool:
        logger.debug(f"[BookTaskManager] add_task called with list_id={list_id}, name={name}")
        if list_id in self.tasks:
            return False
        
        task = BookTask(
            album_id=album_id,
            album_name=album_name,
            album_artist=album_artist,
            list_id=list_id,
            name=name,
            url=url,
            audio_url=audio_url,
            is_parsed=is_parsed
        )
        self.tasks[list_id] = task
        return True

    def add_tasks_batch(self, books: List[Dict]) -> int:
        logger.debug(f"[BookTaskManager] add_tasks_batch called with {len(books)} books")
        added_count = 0
        for book in books:
            if self.add_task(
                album_id=book.get('album_id', 0),
                album_name=book.get('album_name', ''),
                album_artist=book.get('album_artist', ''),
                list_id=book.get('list_id', 0),
                name=book.get('name', ''),
                url=book.get('url', ''),
                audio_url=book.get('audio_url', ''),
                is_parsed=book.get('is_parsed', False)
            ):
                added_count += 1
        return added_count

    def incremental_update(self, new_books: List[Dict]) -> Dict:
        logger.debug(f"[BookTaskManager] incremental_update called with {len(new_books)} books")
        added = []
        duplicated = []
        
        for book in new_books:
            list_id = book.get('list_id', 0)
            if list_id == 0:
                continue
                
            if list_id in self.tasks:
                duplicated.append(list_id)
            else:
                if self.add_task(
                    album_id=book.get('album_id', 0),
                    album_name=book.get('album_name', ''),
                    album_artist=book.get('album_artist', ''),
                    list_id=list_id,
                    name=book.get('name', ''),
                    url=book.get('url', ''),
                    audio_url=book.get('audio_url', ''),
                    is_parsed=book.get('is_parsed', False)
                ):
                    added.append(list_id)
        
        return {
            'added': added,
            'duplicated': duplicated,
            'added_count': len(added),
            'duplicated_count': len(duplicated)
        }

    def is_task_occupied(self, list_id: int) -> bool:
        logger.debug(f"[BookTaskManager] is_task_occupied called with list_id={list_id}")
        return list_id in self.occupied_tasks

    def set_task_occupied(self, list_id: int, occupied: bool = True):
        logger.debug(f"[BookTaskManager] set_task_occupied called with list_id={list_id}, occupied={occupied}")
        if occupied:
            self.occupied_tasks.add(list_id)
        else:
            self.occupied_tasks.discard(list_id)

    def get_unparsed_books(self) -> List[BookTask]:
        logger.debug(f"[BookTaskManager] get_unparsed_books called")
        return [task for task in self.tasks.values() if not task.is_parsed]

    def get_unparsed_urls(self) -> List[str]:
        logger.debug(f"[BookTaskManager] get_unparsed_urls called")
        return [task.url for task in self.tasks.values() if not task.is_parsed]

    def get_undownloaded_books(self) -> List[BookTask]:
        logger.debug(f"[BookTaskManager] get_undownloaded_books called")
        return [task for task in self.tasks.values() if not task.is_downloaded]

    def update_parsed_status(self, list_id: int, is_parsed: bool = True) -> bool:
        logger.debug(f"[BookTaskManager] update_parsed_status called with list_id={list_id}, is_parsed={is_parsed}")
        if list_id not in self.tasks:
            return False
        
        self.tasks[list_id].is_parsed = is_parsed
        if is_parsed:
            self.tasks[list_id].parsed_time = time.strftime("%Y-%m-%d %H:%M:%S")
        return True

    def update_downloaded_status(self, list_id: int, is_downloaded: bool = True) -> bool:
        logger.debug(f"[BookTaskManager] update_downloaded_status called with list_id={list_id}, is_downloaded={is_downloaded}")
        if list_id not in self.tasks:
            return False
        
        self.tasks[list_id].is_downloaded = is_downloaded
        if is_downloaded:
            self.tasks[list_id].downloaded_time = time.strftime("%Y-%m-%d %H:%M:%S")
        return True

    def update_audio_url(self, list_id: int, audio_url: str) -> bool:
        logger.debug(f"[BookTaskManager] update_audio_url called with list_id={list_id}")
        if list_id not in self.tasks:
            return False
        
        self.tasks[list_id].audio_url = audio_url
        return True

    def reset_parsed_status(self, list_id: int) -> bool:
        """重置解析状态，清除audio_url并将is_parsed设为False"""
        logger.debug(f"[BookTaskManager] reset_parsed_status called with list_id={list_id}")
        if list_id not in self.tasks:
            return False
        
        self.tasks[list_id].audio_url = ""
        self.tasks[list_id].is_parsed = False
        self.tasks[list_id].parsed_time = ""
        return True

    def reset_download_status(self, list_id: int) -> bool:
        """重置下载状态，将is_downloaded设为False"""
        logger.debug(f"[BookTaskManager] reset_download_status called with list_id={list_id}")
        if list_id not in self.tasks:
            return False
        
        self.tasks[list_id].is_downloaded = False
        self.tasks[list_id].downloaded_time = ""
        return True

    def reset_all_download_status(self) -> int:
        """重置所有任务的下载状态，返回重置的任务数量"""
        logger.debug(f"[BookTaskManager] reset_all_download_status called")
        reset_count = 0
        for task in self.tasks.values():
            if task.is_downloaded:
                task.is_downloaded = False
                task.downloaded_time = ""
                reset_count += 1
        return reset_count

    def update_task_metadata(self, list_id: int, name: str = None, url: str = None) -> bool:
        #logger.debug(f"[BookTaskManager] update_task_metadata called with list_id={list_id}")
        if list_id not in self.tasks:
            return False
        
        task = self.tasks[list_id]
        if name is not None:
            task.name = name
        if url is not None:
            task.url = url
        
        self.save()
        return True

    def get_audio_info(self, list_id: int) -> Optional[Dict]:
        #logger.debug(f"[BookTaskManager] get_audio_info called with list_id={list_id}")
        task = self.tasks.get(list_id)
        if task and task.is_parsed:
            return {
                'name': task.name,
                'artist': task.album_artist,
                'album_name': task.album_name,
                'url': task.audio_url or task.url
            }
        return None

    def get_all_audio_infos(self) -> List[Dict]:
        logger.debug(f"[BookTaskManager] get_all_audio_infos called")
        audio_infos = []
        for task in self.tasks.values():
            if task.is_parsed:
                audio_infos.append({
                    'name': task.name,
                    'artist': task.album_artist,
                    'album_name': task.album_name,
                    'url': task.audio_url or task.url
                })
        return audio_infos

    def get_task(self, list_id: int) -> Optional[BookTask]:
        logger.debug(f"[BookTaskManager] get_task called with list_id={list_id}")
        return self.tasks.get(list_id)

    def get_all_tasks(self) -> List[BookTask]:
        logger.debug(f"[BookTaskManager] get_all_tasks called")
        return list(self.tasks.values())

    def get_tasks_by_album(self, album_id: int) -> List[BookTask]:
        logger.debug(f"[BookTaskManager] get_tasks_by_album called with album_id={album_id}")
        return [task for task in self.tasks.values() if task.album_id == album_id]
    
    def get_list_ids_by_album(self, album_id: int) -> List[str]:
        logger.debug(f"[BookTaskManager] get_list_ids_by_album called with album_id={album_id}")
        return [task.list_id for task in self.tasks.values() if task.album_id == album_id]

    def update_album_metadata(self, album_id: int, new_name: str = None, new_artist: str = None) -> bool:
        logger.debug(f"[BookTaskManager] update_album_metadata called with album_id={album_id}")
        tasks = self.get_tasks_by_album(album_id)
        if not tasks:
            return False
        
        for task in tasks:
            if new_name is not None:
                task.album_name = new_name
            if new_artist is not None:
                task.album_artist = new_artist
        
        self.save()
        return True

    def remove_task(self, list_id: int) -> bool:
        logger.debug(f"[BookTaskManager] remove_task called with list_id={list_id}")
        if list_id in self.tasks:
            del self.tasks[list_id]
            self.occupied_tasks.discard(list_id)
            return True
        return False

    def save(self) -> bool:
        logger.debug(f"[BookTaskManager] save called")
        try:
            file_path = self._get_tasks_file_path()
            logger.info(f"开始保存任务到: {file_path}")
            data = {
                'version': self.CONFIG_VERSION,
                'tasks': {str(list_id): task.to_dict() for list_id, task in self.tasks.items()},
                'occupied_tasks': list(self.occupied_tasks)
            }
            
            logger.info(f"准备保存 {len(self.tasks)} 个任务")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"任务保存成功")
            return True
        except Exception as e:
            logger.error(f"保存任务失败: {e}", exc_info=True)
            return False

    def load(self) -> tuple:
        logger.debug(f"[BookTaskManager] load called")
        try:
            file_path = self._get_tasks_file_path()
            logger.info(f"尝试加载任务文件: {file_path}")
            if not os.path.exists(file_path):
                logger.warning(f"任务文件不存在: {file_path}")
                return (False, "file_not_found")
            
            logger.info(f"任务文件存在，正在读取...")
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            saved_version = data.get('version', '')
            if saved_version != self.CONFIG_VERSION:
                logger.error(f"配置文件版本不匹配: 期望 {self.CONFIG_VERSION}, 实际 {saved_version}")
                return (False, "version_mismatch")
            
            logger.info(f"JSON数据加载成功")
            self.tasks = {}
            for list_id, task_data in data.get('tasks', {}).items():
                try:
                    key = int(list_id)
                except ValueError:
                    key = list_id
                self.tasks[key] = BookTask.from_dict(task_data)
            
            self.occupied_tasks = set(data.get('occupied_tasks', []))
            
            logger.info(f"成功加载 {len(self.tasks)} 个任务，occupied_tasks: {self.occupied_tasks}")
            return (True, "success")
        except Exception as e:
            logger.error(f"加载任务失败: {e}", exc_info=True)
            return (False, "error")

    def save_book_config(self, list_id: int) -> bool:
        logger.debug(f"[BookTaskManager] save_book_config called with list_id={list_id}")
        if list_id not in self.tasks:
            return False
        
        try:
            task = self.tasks[list_id]
            with open(self._get_book_config_path(list_id), 'w', encoding='utf-8') as f:
                json.dump(task.to_dict(), f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存书籍配置失败: {e}")
            return False

    def load_book_config(self, list_id: int) -> Optional[BookTask]:
        logger.debug(f"[BookTaskManager] load_book_config called with list_id={list_id}")
        try:
            file_path = self._get_book_config_path(list_id)
            if not os.path.exists(file_path):
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return BookTask.from_dict(data)
        except Exception as e:
            print(f"加载书籍配置失败: {e}")
            return None

    def save_all_book_configs(self) -> int:
        logger.debug(f"[BookTaskManager] save_all_book_configs called")
        saved_count = 0
        for list_id in self.tasks:
            if self.save_book_config(list_id):
                saved_count += 1
        return saved_count

    def get_statistics(self) -> Dict:
        logger.debug(f"[BookTaskManager] get_statistics called")
        total = len(self.tasks)
        parsed = sum(1 for t in self.tasks.values() if t.is_parsed)
        downloaded = sum(1 for t in self.tasks.values() if t.is_downloaded)
        occupied = len(self.occupied_tasks)
        
        return {
            'total': total,
            'parsed': parsed,
            'unparsed': total - parsed,
            'downloaded': downloaded,
            'undownloaded': total - downloaded,
            'occupied': occupied
        }

    def clear(self):
        logger.debug(f"[BookTaskManager] clear called")
        self.tasks.clear()
        self.occupied_tasks.clear()

    def __len__(self):
        logger.debug(f"[BookTaskManager] __len__ called")
        return len(self.tasks)

    def __repr__(self):
        logger.debug(f"[BookTaskManager] __repr__ called")
        stats = self.get_statistics()
        return f"BookTaskManager(total={stats['total']}, parsed={stats['parsed']}, downloaded={stats['downloaded']})"