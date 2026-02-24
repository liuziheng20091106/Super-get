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
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'BookTask':
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
        config_path = os.path.join(os.path.dirname(__file__), self.CONFIG_DIR)
        if not os.path.exists(config_path):
            os.makedirs(config_path)

    def _get_tasks_file_path(self) -> str:
        return os.path.join(os.path.dirname(__file__), self.CONFIG_DIR, self.TASKS_FILE)

    def _get_book_config_path(self, book_id: int) -> str:
        return os.path.join(os.path.dirname(__file__), self.CONFIG_DIR, f"book_{book_id}.json")

    def add_task(self, album_id: int, album_name: str, album_artist: str, 
                 list_id: int, name: str, url: str, 
                 audio_url: str = "", is_parsed: bool = False) -> bool:
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
        return list_id in self.occupied_tasks

    def set_task_occupied(self, list_id: int, occupied: bool = True):
        if occupied:
            self.occupied_tasks.add(list_id)
        else:
            self.occupied_tasks.discard(list_id)

    def get_unparsed_books(self) -> List[BookTask]:
        return [task for task in self.tasks.values() if not task.is_parsed]

    def get_unparsed_urls(self) -> List[str]:
        return [task.url for task in self.tasks.values() if not task.is_parsed]

    def get_undownloaded_books(self) -> List[BookTask]:
        return [task for task in self.tasks.values() if not task.is_downloaded]

    def update_parsed_status(self, list_id: int, is_parsed: bool = True) -> bool:
        if list_id not in self.tasks:
            return False
        
        self.tasks[list_id].is_parsed = is_parsed
        if is_parsed:
            self.tasks[list_id].parsed_time = time.strftime("%Y-%m-%d %H:%M:%S")
        return True

    def update_downloaded_status(self, list_id: int, is_downloaded: bool = True) -> bool:
        if list_id not in self.tasks:
            return False
        
        self.tasks[list_id].is_downloaded = is_downloaded
        if is_downloaded:
            self.tasks[list_id].downloaded_time = time.strftime("%Y-%m-%d %H:%M:%S")
        return True

    def update_audio_url(self, list_id: int, audio_url: str) -> bool:
        if list_id not in self.tasks:
            return False
        
        self.tasks[list_id].audio_url = audio_url
        return True

    def get_audio_info(self, list_id: int) -> Optional[Dict]:
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
        return self.tasks.get(list_id)

    def get_all_tasks(self) -> List[BookTask]:
        return list(self.tasks.values())

    def get_tasks_by_album(self, album_id: int) -> List[BookTask]:
        return [task for task in self.tasks.values() if task.album_id == album_id]
    
    def get_list_ids_by_album(self, album_id: int) -> List[str]:
        return [task.list_id for task in self.tasks.values() if task.album_id == album_id]

    def remove_task(self, list_id: int) -> bool:
        if list_id in self.tasks:
            del self.tasks[list_id]
            self.occupied_tasks.discard(list_id)
            return True
        return False

    def save(self) -> bool:
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
        saved_count = 0
        for list_id in self.tasks:
            if self.save_book_config(list_id):
                saved_count += 1
        return saved_count

    def get_statistics(self) -> Dict:
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
        self.tasks.clear()
        self.occupied_tasks.clear()

    def __len__(self):
        return len(self.tasks)

    def __repr__(self):
        stats = self.get_statistics()
        return f"BookTaskManager(total={stats['total']}, parsed={stats['parsed']}, downloaded={stats['downloaded']})"