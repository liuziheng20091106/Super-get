import sys
import json
import time
import queue
import threading
import requests
import urllib3
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTableView, QHeaderView, QPushButton, QLineEdit,
    QTextEdit, QGroupBox, QDialog, QListWidget, QListWidgetItem,
    QMessageBox, QAbstractItemView, QTabWidget, QProgressBar,
    QStatusBar, QMenuBar, QMenu, QFileDialog, QFrame, QSplitter,
    QScrollArea, QCheckBox, QComboBox, QSpinBox
)
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel, pyqtSignal, QThread, QTimer, QUrl
from PyQt6.QtGui import QAction, QFont, QColor, QPalette, QIcon, QPixmap
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

from book_task_manager import BookTaskManager, BookTask
from search_parser import SearchClient, SearchResult
from scraper import AudioScraper
from downloader import AudioDownloader, AudioInfo
from config import Config


def warmup_requests():
    urls = [
        "https://i275.com/play/29690/16921470.html",
        "https://m.i275.com/play/29690/16921470.html",
        "https://i275.com/",
        "https://m.i275.com/"
    ]
    
    headers = Config.get_headers()
    
    for url in urls:
        try:
            requests.get(url, headers=headers, timeout=10, verify=False)
            print(f"预热请求成功: {url}")
        except Exception as e:
            print(f"预热请求失败: {url}, 错误: {e}")


class SearchThread(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, keyword):
        super().__init__()
        self.keyword = keyword

    def run(self):
        try:
            client = SearchClient()
            results = client.search(self.keyword)
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class ParseThread(QThread):
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, urls, list_ids, manager):
        super().__init__()
        self.urls = urls
        self.list_ids = list_ids
        self.manager = manager

    def run(self):
        try:
            scraper = AudioScraper()
            scraper.init_session()
            
            results = []
            total = len(self.urls)
            
            for i, (url, list_id) in enumerate(zip(self.urls, self.list_ids)):
                self.progress.emit(i + 1, total, url)
                audio_info = scraper.extract_audio_info(url)
                if audio_info:
                    audio_info['list_id'] = list_id
                    results.append(audio_info)
            
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class FetchChapterListThread(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, album_id: int):
        super().__init__()
        self.album_id = album_id

    def run(self):
        try:
            from book_scraper import download_book_page
            from extractor import LinkExtractor
            
            html_content = download_book_page(self.album_id)
            
            if not html_content:
                self.error.emit("无法下载书籍页面")
                return
            
            chapters = LinkExtractor.extract_chapters(html_content)
            
            if not chapters:
                self.error.emit("未找到章节列表")
                return
            
            self.finished.emit(chapters)
        except Exception as e:
            self.error.emit(str(e))


class ParseAlbumThread(QThread):
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(int, int)
    error = pyqtSignal(str)
    saved = pyqtSignal()

    def __init__(self, album_id: int, album_name: str, album_artist: str, manager, resume_list_ids: list = None):
        super().__init__()
        self.album_id = album_id
        self.album_name = album_name
        self.album_artist = album_artist
        self.manager = manager
        self.resume_list_ids = resume_list_ids or []
        self._stop_flag = False

    def stop(self):
        self._stop_flag = True

    def run(self):
        try:
            from book_scraper import download_book_page
            from extractor import LinkExtractor
            from scraper import AudioScraper
            
            self.progress.emit(0, 100, "正在下载书籍页面...")
            html_content = download_book_page(self.album_id)
            
            if not html_content:
                self.error.emit("无法下载书籍页面")
                return
            
            if self._stop_flag:
                self.finished.emit(0, 0)
                return
            
            self.progress.emit(10, 100, "正在提取章节列表...")
            chapters = LinkExtractor.extract_chapters(html_content)
            
            if not chapters:
                self.error.emit("未找到章节列表")
                return
            
            existing_list_ids = set(self.manager.get_list_ids_by_album(self.album_id))
            
            new_chapters = []
            for chapter in chapters:
                if chapter.chapter_id not in existing_list_ids:
                    new_chapters.append(chapter)
            
            if not new_chapters:
                self.progress.emit(100, 100, "没有新章节需要解析")
                self.finished.emit(0, 0)
                return
            
            self.progress.emit(20, 100, f"找到 {len(new_chapters)} 个新章节，正在解析音频URL...")
            
            scraper = AudioScraper()
            scraper.init_session()
            
            play_urls = LinkExtractor.build_play_urls([c.chapter_id for c in new_chapters])
            
            books = []
            total = len(play_urls)
            parsed_count = 0
            
            for i, (chapter, url) in enumerate(zip(new_chapters, play_urls)):
                if self._stop_flag:
                    break
                
                self.progress.emit(20 + int(70 * (i + 1) / total), 100, f"解析第 {i+1}/{total} 集")
                
                audio_info = scraper.extract_audio_info(url)
                
                if audio_info:
                    books.append({
                        'album_id': self.album_id,
                        'album_name': self.album_name,
                        'album_artist': self.album_artist,
                        'list_id': chapter.chapter_id,
                        'name': chapter.title,
                        'url': url,
                        'audio_url': audio_info.get('url', ''),
                        'is_parsed': True
                    })
                    parsed_count += 1
                else:
                    books.append({
                        'album_id': self.album_id,
                        'album_name': self.album_name,
                        'album_artist': self.album_artist,
                        'list_id': chapter.chapter_id,
                        'name': chapter.title,
                        'url': url,
                        'audio_url': '',
                        'is_parsed': False
                    })
                
                self.manager.incremental_update(books)
                for book in books:
                    list_id = book['list_id']
                    if list_id in self.manager.tasks and book.get('audio_url'):
                        self.manager.update_audio_url(list_id, book['audio_url'])
                self.manager.save()
                self.saved.emit()
                books = []
            
            self.progress.emit(100, 100, "解析完成")
            added = parsed_count if not self._stop_flag else 0
            self.finished.emit(added, parsed_count)
            
        except Exception as e:
            self.error.emit(str(e))


class DownloadThread(QThread):
    progress = pyqtSignal(str, str)
    finished = pyqtSignal(int, int)
    error = pyqtSignal(str)

    def __init__(self, audio_infos, download_dir):
        super().__init__()
        self.audio_infos = audio_infos
        self.download_dir = download_dir

    def run(self):
        try:
            downloader = AudioDownloader(
                max_workers=self.config.MAX_WORKERS,
                max_retries=self.config.MAX_RETRIES,
                download_dir=self.download_dir
            )
            
            success_count = 0
            total = len(self.audio_infos)
            
            for i, info in enumerate(self.audio_infos):
                audio_info = AudioInfo(
                    name=info.get('name', '未知'),
                    artist=info.get('artist', '未知'),
                    url=info.get('url', '')
                )
                audio_info.generate_file_path(self.download_dir)
                
                self.progress.emit(audio_info.name, "downloading")
                
                if downloader.download_single(audio_info):
                    success_count += 1
                    self.progress.emit(audio_info.name, "success")
                else:
                    self.progress.emit(audio_info.name, "failed")
            
            self.finished.emit(success_count, total)
        except Exception as e:
            self.error.emit(str(e))


class BookTaskTableModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tasks = []
        self.headers = ['序号', '名称', '解析状态', '下载状态', '添加时间']

    def rowCount(self, parent=QModelIndex()):
        return len(self.tasks)

    def columnCount(self, parent=QModelIndex()):
        return len(self.headers)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            return self.headers[section]
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()

        if row >= len(self.tasks):
            return None

        task = self.tasks[row]

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return str(row + 1)
            elif col == 1:
                return task.name
            elif col == 2:
                return "✓" if task.is_parsed else "✗"
            elif col == 3:
                return "✓" if task.is_downloaded else "✗"
            elif col == 4:
                return task.added_time
        elif role == Qt.ItemDataRole.BackgroundRole:
            if task.is_downloaded:
                return QColor(50, 80, 50)
            elif task.is_parsed:
                return QColor(80, 80, 50)
        elif role == Qt.ItemDataRole.ToolTipRole:
            return self._build_tooltip(task)

        return None

    def _build_tooltip(self, task: BookTask) -> str:
        return (f"专辑名: {task.album_name}\n"
                f"专辑ID: {task.album_id}\n"
                f"艺术家: {task.album_artist}\n"
                f"URL: {task.url}\n"
                f"解析: {'是' if task.is_parsed else '否'}\n"
                f"下载: {'是' if task.is_downloaded else '否'}")

    def get_task(self, row: int) -> BookTask:
        if 0 <= row < len(self.tasks):
            return self.tasks[row]
        return None

    def set_tasks(self, tasks: list):
        self.beginResetModel()
        self.tasks = tasks
        self.endResetModel()

    def update_task(self, row: int):
        if 0 <= row < len(self.tasks):
            self.dataChanged.emit(self.index(row, 0), self.index(row, self.columnCount() - 1))

    def add_tasks(self, tasks: list):
        start = len(self.tasks)
        self.beginInsertRows(QModelIndex(), start, start + len(tasks) - 1)
        self.tasks.extend(tasks)
        self.endInsertRows()

    def remove_task(self, row: int):
        if 0 <= row < len(self.tasks):
            self.beginRemoveRows(QModelIndex(), row, row)
            del self.tasks[row]
            self.endRemoveRows()


class AlbumListWidget(QWidget):
    album_selected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.albums = {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QLabel("📚 书籍列表")
        header.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
                background-color: #2d2d2d;
                border-bottom: 1px solid #3d3d3d;
            }
        """)
        layout.addWidget(header)

        self.album_list = QListWidget()
        self.album_list.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e;
                border: none;
                color: #e0e0e0;
            }
            QListWidget::item {
                padding: 12px;
                border-bottom: 1px solid #2d2d2d;
            }
            QListWidget::item:selected {
                background-color: #667eea;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #3d3d3d;
            }
        """)
        self.album_list.itemClicked.connect(self.on_item_clicked)
        layout.addWidget(self.album_list, 1)

    def set_albums(self, albums: dict):
        self.albums = albums
        self.album_list.clear()
        for album_id, info in albums.items():
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, album_id)
            item.setText(f"{info['name']}\n{info['artist']}")
            item.setToolTip(f"ID: {album_id}\n任务数: {info['task_count']}")
            self.album_list.addItem(item)

    def on_item_clicked(self, item):
        album_id = item.data(Qt.ItemDataRole.UserRole)
        self.album_selected.emit(album_id)

    def add_album(self, album_id: int, name: str, artist: str, task_count: int = 0):
        self.albums[album_id] = {'name': name, 'artist': artist, 'task_count': task_count}
        self.set_albums(self.albums)

    def update_album(self, album_id: int, task_count: int):
        if album_id in self.albums:
            self.albums[album_id]['task_count'] = task_count
            self.set_albums(self.albums)

    def remove_album(self, album_id: int):
        if album_id in self.albums:
            del self.albums[album_id]
            self.set_albums(self.albums)


class ResultItemWidget(QWidget):
    def __init__(self, result: SearchResult, parent=None):
        super().__init__(parent)
        self.result = result
        self.init_ui()
    
    def init_ui(self):
        self.setFixedHeight(120)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(15)
        
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(70, 100)
        self.cover_label.setScaledContents(False)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setStyleSheet("""
            QLabel {
                background-color: #2d2d2d;
                border-radius: 6px;
                border: 1px solid #3d3d3d;
            }
        """)
        
        if self.result.cover_url:
            self.load_cover()
        
        layout.addWidget(self.cover_label)
        
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(4)
        
        title_label = QLabel(self.result.title)
        title_label.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #e0e0e0;")
        title_label.setMaximumWidth(350)
        title_label.setWordWrap(True)
        
        narrator_label = QLabel(f"演播：{self.result.narrator}")
        narrator_label.setFont(QFont("Microsoft YaHei", 9))
        narrator_label.setStyleSheet("color: #888;")
        
        author_label = QLabel(f"作者：{self.result.author}")
        author_label.setFont(QFont("Microsoft YaHei", 9))
        author_label.setStyleSheet("color: #888;")
        
        desc = self.result.description[:60] + "..." if len(self.result.description) > 60 else self.result.description
        desc_label = QLabel(desc)
        desc_label.setFont(QFont("Microsoft YaHei", 8))
        desc_label.setStyleSheet("color: #666;")
        desc_label.setMaximumWidth(350)
        desc_label.setWordWrap(True)
        
        info_layout.addWidget(title_label)
        info_layout.addWidget(narrator_label)
        info_layout.addWidget(author_label)
        info_layout.addWidget(desc_label)
        info_layout.addStretch()
        
        layout.addLayout(info_layout)
        
        id_label = QLabel(f"ID: {self.result.book_id}")
        id_label.setFont(QFont("Consolas", 9))
        id_label.setStyleSheet("color: #9b59b6; font-weight: bold;")
        
        layout.addWidget(id_label, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        
        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
            }
            QWidget:hover {
                background-color: #3d3d3d;
            }
        """)
    
    def load_cover(self):
        def handle_reply(reply):
            if reply.error() == QNetworkReply.NetworkError.NoError:
                pixmap = QPixmap()
                pixmap.loadFromData(reply.readAll())
                if not pixmap.isNull():
                    scaled = pixmap.scaled(70, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    self.cover_label.setPixmap(scaled)
            reply.deleteLater()
        
        if self.result.cover_url and self.result.cover_url.startswith('http'):
            self.manager = QNetworkAccessManager()
            request = QNetworkRequest(QUrl(self.result.cover_url))
            reply = self.manager.get(request)
            reply.finished.connect(lambda: handle_reply(reply))


class SearchResultDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_book = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("搜索有声小说")
        self.setMinimumSize(600, 500)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
            }
            QLineEdit {
                padding: 10px 15px;
                border: 2px solid #3d3d3d;
                border-radius: 25px;
                font-size: 14px;
                background-color: #2d2d2d;
                color: #e0e0e0;
            }
            QLineEdit:focus {
                border-color: #667eea;
            }
            QLineEdit::placeholder {
                color: #888;
            }
            QPushButton {
                padding: 10px 25px;
                border: none;
                border-radius: 25px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton#search_btn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #667eea, stop:1 #764ba2);
                color: white;
            }
            QPushButton#search_btn:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #5a6fd6, stop:1 #6a4190);
            }
            QPushButton#search_btn:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4e5fc2, stop:1 #5e377e);
            }
            QPushButton#search_btn:disabled {
                background: #4d4d4d;
                color: #888;
            }
            QListWidget {
                border: none;
                background-color: #2d2d2d;
                color: #e0e0e0;
            }
            QListWidget::item {
                border-bottom: 1px solid #3d3d3d;
                padding: 10px;
            }
            QListWidget::item:selected {
                background-color: #667eea;
                color: white;
            }
            QLabel {
                color: #e0e0e0;
            }
            QLabel#title_label {
                font-size: 20px;
                font-weight: bold;
                color: white;
            }
            QLabel#result_count {
                color: #888;
                font-size: 13px;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        header_widget = QWidget()
        header_widget.setFixedHeight(120)
        header_widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #667eea, stop:1 #764ba2);
            }
        """)
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(20, 20, 20, 20)

        title_label = QLabel("搜索有声小说")
        title_label.setObjectName("title_label")
        header_layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignCenter)

        search_layout = QHBoxLayout()
        search_layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入书名、作者或演播名称...")
        self.search_input.setFixedHeight(45)
        self.search_input.returnPressed.connect(self.do_search)

        self.search_btn = QPushButton("搜索")
        self.search_btn.setObjectName("search_btn")
        self.search_btn.setFixedSize(90, 45)
        self.search_btn.clicked.connect(self.do_search)

        search_layout.addWidget(self.search_input, 1)
        search_layout.addWidget(self.search_btn)

        header_layout.addLayout(search_layout)

        main_layout.addWidget(header_widget)

        self.result_count_label = QLabel("请输入关键词搜索")
        self.result_count_label.setObjectName("result_count")
        self.result_count_label.setMargin(15)
        main_layout.addWidget(self.result_count_label)

        self.result_list = QListWidget()
        self.result_list.setSpacing(0)
        self.result_list.itemClicked.connect(self.on_item_clicked)
        self.result_list.itemDoubleClicked.connect(self.on_item_double_clicked)

        main_layout.addWidget(self.result_list, 1)

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #888; padding: 10px;")
        main_layout.addWidget(self.status_label)

    def do_search(self):
        keyword = self.search_input.text().strip()
        if not keyword:
            self.status_label.setText("请输入搜索关键词")
            return

        self.status_label.setText("搜索中...")
        self.result_list.clear()
        self.results = []
        self.search_btn.setEnabled(False)

        self.search_thread = SearchThread(keyword)
        self.search_thread.finished.connect(self.on_search_finished)
        self.search_thread.error.connect(self.on_search_error)
        self.search_thread.start()

    def on_search_finished(self, results):
        self.search_btn.setEnabled(True)
        self.status_label.setText("")

        if not results:
            self.result_count_label.setText("未找到相关结果")
            return

        self.result_count_label.setText(f"找到 {len(results)} 个结果")
        self.results = results

        for result in results:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, result)

            widget = ResultItemWidget(result)
            item.setSizeHint(widget.sizeHint())

            self.result_list.addItem(item)
            self.result_list.setItemWidget(item, widget)

    def on_search_error(self, error_msg):
        self.search_btn.setEnabled(True)
        self.status_label.setText(f"搜索失败: {error_msg}")

    def on_item_clicked(self, item):
        pass

    def on_item_double_clicked(self, item):
        result = item.data(Qt.ItemDataRole.UserRole)
        if result:
            self.selected_book_id = result.book_id
            self.selected_book = result
            self.accept()

    def get_selected_book(self):
        return self.selected_book


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.manager = BookTaskManager()
        self.config = Config()
        self.current_album_id = None
        self.current_album_name = ""
        self.current_album_artist = ""
        
        self.parse_thread = None
        self.download_thread = None
        
        self.init_ui()
        self.load_data()

    def init_ui(self):
        self.setWindowTitle("有声小说下载管理器")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumSize(1000, 700)

        self._create_menu_bar()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.album_list_widget = AlbumListWidget()
        self.album_list_widget.setFixedWidth(220)
        self.album_list_widget.album_selected.connect(self.on_album_selected)
        main_layout.addWidget(self.album_list_widget)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(10)

        right_layout.addWidget(self._create_toolbar())
        right_layout.addWidget(self._create_album_info())
        right_layout.addWidget(self._create_table(), 1)
        right_layout.addWidget(self._create_progress_group())

        main_layout.addWidget(right_panel, 1)

        self._apply_styles()

    def _create_menu_bar(self):
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border-bottom: 1px solid #3d3d3d;
            }
            QMenuBar::item:selected {
                background-color: #3d3d3d;
            }
            QMenu {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #3d3d3d;
            }
            QMenu::item:selected {
                background-color: #3d3d3d;
            }
        """)
        
        file_menu = menubar.addMenu("文件")
        
        action_search = QAction("搜索添加", self)
        action_search.triggered.connect(self.show_search_dialog)
        file_menu.addAction(action_search)
        
        action_import = QAction("从文件导入", self)
        action_import.triggered.connect(self.import_from_file)
        file_menu.addAction(action_import)
        
        file_menu.addSeparator()
        
        action_exit = QAction("退出", self)
        action_exit.triggered.connect(self.close)
        file_menu.addAction(action_exit)
        
        task_menu = menubar.addMenu("任务")
        
        action_parse = QAction("解析选中", self)
        action_parse.triggered.connect(self.parse_selected)
        task_menu.addAction(action_parse)
        
        action_parse_all = QAction("解析全部未解析", self)
        action_parse_all.triggered.connect(self.parse_all_unparsed)
        task_menu.addAction(action_parse_all)
        
        task_menu.addSeparator()
        
        action_download = QAction("下载选中", self)
        action_download.triggered.connect(self.download_selected)
        task_menu.addAction(action_download)
        
        action_download_all = QAction("下载全部未下载", self)
        action_download_all.triggered.connect(self.download_all_undownloaded)
        task_menu.addAction(action_download_all)
        
        help_menu = menubar.addMenu("帮助")
        
        action_about = QAction("关于", self)
        action_about.triggered.connect(self.show_about)
        help_menu.addAction(action_about)

    def _create_toolbar(self) -> QWidget:
        widget = QWidget()
        widget.setStyleSheet("background-color: #2d2d2d;")
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 5, 0, 5)

        btn_style = """
            QPushButton {
                padding: 8px 15px;
                border-radius: 4px;
                background-color: #4CAF50;
                color: white;
                border: none;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:pressed { background-color: #3d8b40; }
            QPushButton:disabled { background-color: #4d4d4d; color: #888; }
        """

        self.btn_search = QPushButton("🔍 搜索添加")
        self.btn_search.setStyleSheet(btn_style)
        self.btn_search.clicked.connect(self.show_search_dialog)
        layout.addWidget(self.btn_search)

        self.btn_import = QPushButton("📁 导入文件")
        self.btn_import.setStyleSheet(btn_style)
        self.btn_import.clicked.connect(self.import_from_file)
        layout.addWidget(self.btn_import)

        layout.addSpacing(20)

        self.btn_parse = QPushButton("⚡ 解析选中")
        self.btn_parse.setStyleSheet(btn_style)
        self.btn_parse.clicked.connect(self.parse_selected)
        layout.addWidget(self.btn_parse)

        self.btn_parse_all = QPushButton("⚡ 解析全部")
        self.btn_parse_all.setStyleSheet(btn_style)
        self.btn_parse_all.clicked.connect(self.parse_all_unparsed)
        layout.addWidget(self.btn_parse_all)

        layout.addSpacing(20)

        self.btn_download = QPushButton("⬇️ 下载选中")
        self.btn_download.setStyleSheet(btn_style)
        self.btn_download.clicked.connect(self.download_selected)
        layout.addWidget(self.btn_download)

        self.btn_download_all = QPushButton("⬇️ 下载全部")
        self.btn_download_all.setStyleSheet(btn_style)
        self.btn_download_all.clicked.connect(self.download_all_undownloaded)
        layout.addWidget(self.btn_download_all)

        layout.addSpacing(20)

        self.btn_stop = QPushButton("⏹ 终止任务")
        self.btn_stop.setStyleSheet(btn_style)
        self.btn_stop.setObjectName("stop_btn")
        self.btn_stop.clicked.connect(self.stop_current_task)
        self.btn_stop.setEnabled(False)
        layout.addWidget(self.btn_stop)

        self.btn_resume = QPushButton("▶️ 继续解析")
        self.btn_resume.setStyleSheet(btn_style)
        self.btn_resume.setObjectName("resume_btn")
        self.btn_resume.clicked.connect(self.resume_parsing)
        layout.addWidget(self.btn_resume)

        layout.addStretch()

        self.btn_clear = QPushButton("🗑️ 清空已完成")
        self.btn_clear.setStyleSheet(btn_style)
        self.btn_clear.clicked.connect(self.clear_completed)
        layout.addWidget(self.btn_clear)

        widget.setLayout(layout)
        return widget

    def _create_album_info(self) -> QGroupBox:
        group = QGroupBox("当前任务信息")
        layout = QHBoxLayout()

        self.album_name_label = QLabel("专辑名: 未加载")
        self.album_id_label = QLabel("专辑ID: -")
        self.album_artist_label = QLabel("艺术家: -")
        self.task_count_label = QLabel("任务数: 0")

        for label in [self.album_name_label, self.album_id_label, 
                      self.album_artist_label, self.task_count_label]:
            label.setStyleSheet("font-size: 13px; padding: 5px; color: #e0e0e0;")
            layout.addWidget(label)

        layout.addStretch()
        group.setLayout(layout)
        return group

    def _create_table(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.table_view = QTableView()
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setShowGrid(True)
        self.table_view.setSortingEnabled(True)

        self.model = BookTaskTableModel()
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.table_view.setModel(self.proxy_model)

        header = self.table_view.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        self.table_view.setColumnWidth(0, 50)
        self.table_view.setColumnWidth(2, 70)
        self.table_view.setColumnWidth(3, 70)

        layout.addWidget(self.table_view)
        widget.setLayout(layout)
        return widget

    def _create_progress_group(self) -> QWidget:
        widget = QWidget()
        widget.setStyleSheet("background-color: #2d2d2d;")
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("等待中...")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                text-align: center;
                background-color: #2d2d2d;
                color: #e0e0e0;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
        """)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #888;")
        layout.addWidget(self.status_label)

        widget.setLayout(layout)
        return widget

    def _apply_styles(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #3d3d3d;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 8px;
                background-color: #2d2d2d;
                color: #e0e0e0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #e0e0e0;
            }
            QTableView {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                gridline-color: #3d3d3d;
                color: #e0e0e0;
            }
            QTableView::item { padding: 5px; color: #e0e0e0; }
            QTableView::item:selected { background-color: #667eea; color: white; }
            QTableView::item:hover { background-color: #3d3d3d; }
            QHeaderView::section {
                background-color: #3d3d3d;
                padding: 8px;
                border: none;
                border-right: 1px solid #4d4d4d;
                border-bottom: 1px solid #4d4d4d;
                font-weight: bold;
                color: #e0e0e0;
            }
            QPushButton {
                padding: 8px 15px;
                border-radius: 4px;
                background-color: #4CAF50;
                color: white;
                border: none;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:pressed { background-color: #3d8b40; }
            QPushButton:disabled { background-color: #4d4d4d; color: #888; }
            QLabel { color: #e0e0e0; }
            QProgressBar {
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                text-align: center;
                background-color: #2d2d2d;
                color: #e0e0e0;
            }
            QProgressBar::chunk { background-color: #4CAF50; }
            QMenuBar { background-color: #2d2d2d; color: #e0e0e0; }
            QMenuBar::item:selected { background-color: #3d3d3d; }
            QMenu { background-color: #2d2d2d; color: #e0e0e0; }
            QMenu::item:selected { background-color: #3d3d3d; }
        """)

    def load_data(self):
        if self.manager.load():
            self._refresh_album_list()
            self.refresh_display()

    def _refresh_album_list(self):
        albums = {}
        for task in self.manager.tasks.values():
            if task.album_id not in albums:
                albums[task.album_id] = {
                    'name': task.album_name,
                    'artist': task.album_artist,
                    'task_count': 0
                }
            albums[task.album_id]['task_count'] += 1
        
        self.album_list_widget.set_albums(albums)

    def refresh_display(self):
        tasks = self.manager.get_all_tasks()
        
        if self.current_album_id is not None:
            tasks = [t for t in tasks if t.album_id == self.current_album_id]
        
        self.model.set_tasks(tasks)
        self._update_album_info()
        self._update_task_count()

    def _update_album_info(self):
        if self.current_album_name:
            self.album_name_label.setText(f"专辑名: {self.current_album_name}")
            self.album_id_label.setText(f"专辑ID: {self.current_album_id}")
            self.album_artist_label.setText(f"艺术家: {self.current_album_artist}")
        else:
            self.album_name_label.setText("专辑名: 未加载")
            self.album_id_label.setText("专辑ID: -")
            self.album_artist_label.setText("艺术家: -")

    def _update_task_count(self):
        stats = self.manager.get_statistics()
        
        if self.current_album_id is not None:
            album_tasks = self.manager.get_tasks_by_album(self.current_album_id)
            album_stats = {
                'total': len(album_tasks),
                'parsed': sum(1 for t in album_tasks if t.is_parsed),
                'downloaded': sum(1 for t in album_tasks if t.is_downloaded)
            }
            self.task_count_label.setText(
                f"总任务: {album_stats['total']} | 已解析: {album_stats['parsed']} | 已下载: {album_stats['downloaded']}"
            )
        else:
            self.task_count_label.setText(
                f"总任务: {stats['total']} | 已解析: {stats['parsed']} | 已下载: {stats['downloaded']}"
            )

    def on_album_selected(self, album_id: int):
        tasks = self.manager.get_tasks_by_album(album_id)
        if tasks:
            self.current_album_id = album_id
            self.current_album_name = tasks[0].album_name
            self.current_album_artist = tasks[0].album_artist
            self.refresh_display()

    def show_search_dialog(self):
        dialog = SearchResultDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            book = dialog.get_selected_book()
            if book:
                self.add_book_from_search(book)

    def add_book_from_search(self, book: SearchResult):
        self.current_album_id = int(book.book_id)
        self.current_album_name = book.title
        self.current_album_artist = book.narrator
        
        self.album_name_label.setText(f"专辑名: {book.title}")
        self.album_id_label.setText(f"专辑ID: {book.book_id}")
        self.album_artist_label.setText(f"艺术家: {book.narrator}")
        
        self._refresh_album_list()
        
        self._fetch_chapter_list_and_ask(book)
    
    def _fetch_chapter_list_and_ask(self, book: SearchResult):
        self.statusBar().showMessage(f"正在获取章节列表: {book.title}...")
        
        self.fetch_thread = FetchChapterListThread(int(book.book_id))
        self.fetch_thread.finished.connect(lambda chapters: self._on_chapters_fetched(book, chapters))
        self.fetch_thread.error.connect(lambda err: self._on_chapters_fetch_error(book, err))
        self.fetch_thread.start()
    
    def _on_chapters_fetched(self, book: SearchResult, chapters: list):
        if not chapters:
            QMessageBox.warning(self, "警告", "未找到章节列表")
            return
        
        existing_list_ids = set(self.manager.get_list_ids_by_album(int(book.book_id)))
        new_chapters = [c for c in chapters if c.chapter_id not in existing_list_ids]
        
        if not new_chapters:
            QMessageBox.information(
                self, "提示",
                f"专辑 '{book.title}' 已全部收录\n共 {len(chapters)} 个章节，无需重复添加"
            )
            return
        
        reply = QMessageBox.question(
            self, "确认添加",
            f"专辑: {book.title}\n"
            f"总章节: {len(chapters)} 个\n"
            f"新增章节: {len(new_chapters)} 个\n\n"
            f"是否开始解析新增章节的音频URL？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._start_parsing_new_chapters(book, new_chapters)
        elif reply == QMessageBox.StandardButton.No:
            self._add_chapters_only(book, new_chapters)
    
    def _on_chapters_fetch_error(self, book: SearchResult, error_msg: str):
        QMessageBox.warning(self, "获取章节列表失败", error_msg)
    
    def _start_parsing_new_chapters(self, book: SearchResult, new_chapters: list):
        self.btn_stop.setEnabled(True)
        self.btn_search.setEnabled(False)
        self.btn_import.setEnabled(False)
        
        self.statusBar().showMessage(f"正在解析 {len(new_chapters)} 个新章节...")
        
        self.parse_thread = ParseAlbumThread(
            int(book.book_id),
            book.title,
            book.narrator,
            self.manager
        )
        self.parse_thread.progress.connect(self.on_parse_progress)
        self.parse_thread.finished.connect(self.on_parse_finished)
        self.parse_thread.error.connect(self.on_parse_error)
        self.parse_thread.saved.connect(self._on_parse_saved)
        self.parse_thread.start()
    
    def _add_chapters_only(self, book: SearchResult, new_chapters: list):
        from extractor import LinkExtractor
        
        play_urls = LinkExtractor.build_play_urls([c.chapter_id for c in new_chapters])
        
        books = []
        for chapter, url in zip(new_chapters, play_urls):
            books.append({
                'album_id': int(book.book_id),
                'album_name': book.title,
                'album_artist': book.narrator,
                'list_id': chapter.chapter_id,
                'name': chapter.title,
                'url': url,
                'audio_url': '',
                'is_parsed': False
            })
        
        result = self.manager.incremental_update(books)
        self.manager.save()
        self._refresh_album_list()
        self.refresh_display()
        
        QMessageBox.information(
            self, "完成",
            f"已添加 {result['added_count']} 个章节到列表\n"
            f"可点击'继续解析'按钮解析音频URL"
        )
    
    def on_parse_progress(self, current: int, total: int, message: str):
        self.statusBar().showMessage(f"解析中 ({current}/{total}): {message}")
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setValue(current)
            self.progress_bar.setFormat(f"{current}% - {message}")
    
    def on_parse_finished(self, added_count: int, parsed_count: int):
        self.manager.save()
        self._refresh_album_list()
        self.refresh_display()
        
        self.btn_stop.setEnabled(False)
        self.btn_search.setEnabled(True)
        self.btn_import.setEnabled(True)
        
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setValue(100)
            self.progress_bar.setFormat("完成")
        
        if added_count > 0:
            self.statusBar().showMessage(f"解析完成，成功解析 {added_count}/{parsed_count} 个章节", 5000)
            QMessageBox.information(
                self, "完成", 
                f"已成功解析专辑: {self.current_album_name}\n成功解析: {added_count}/{parsed_count} 个章节"
            )
        else:
            self.statusBar().showMessage("没有新章节需要解析", 5000)
    
    def on_parse_error(self, error_msg: str):
        self.btn_stop.setEnabled(False)
        self.btn_search.setEnabled(True)
        self.btn_import.setEnabled(True)
        
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("解析失败")
        
        self.statusBar().showMessage(f"解析失败: {error_msg}", 5000)
        QMessageBox.warning(self, "解析失败", error_msg)
    
    def stop_current_task(self):
        if hasattr(self, 'parse_thread') and self.parse_thread.isRunning():
            self.parse_thread.stop()
            self.statusBar().showMessage("正在终止任务...", 3000)
    
    def resume_parsing(self):
        if self.current_album_id is None:
            QMessageBox.warning(self, "警告", "请先选择一个专辑")
            return
        
        unparsed_tasks = [t for t in self.manager.get_tasks_by_album(self.current_album_id) 
                         if not t.is_parsed]
        
        if not unparsed_tasks:
            QMessageBox.information(self, "提示", "所有章节已解析完成")
            return
        
        reply = QMessageBox.question(
            self, "继续解析",
            f"当前专辑有 {len(unparsed_tasks)} 个章节未解析，是否继续解析？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._start_parsing_unparsed(unparsed_tasks)
    
    def _start_parsing_unparsed(self, unparsed_tasks: list):
        self.btn_stop.setEnabled(True)
        self.btn_search.setEnabled(False)
        self.btn_import.setEnabled(False)
        
        self.statusBar().showMessage(f"正在解析 {len(unparsed_tasks)} 个未解析章节...")
        
        self.parse_thread = ParseAlbumThread(
            self.current_album_id,
            self.current_album_name,
            self.current_album_artist,
            self.manager,
            resume_list_ids=[t.list_id for t in unparsed_tasks]
        )
        self.parse_thread.progress.connect(self.on_parse_progress)
        self.parse_thread.finished.connect(self.on_parse_finished)
        self.parse_thread.error.connect(self.on_parse_error)
        self.parse_thread.saved.connect(self._on_parse_saved)
        self.parse_thread.start()
    
    def _on_parse_saved(self):
        self._refresh_album_list()
        self.refresh_display()

    def import_from_file(self):
        if self.current_album_id is None:
            QMessageBox.warning(self, "警告", "请先搜索并选择一个书籍")
            return
            
        filename, _ = QFileDialog.getOpenFileName(
            self, "选择文件", "", "文本文件 (*.txt);;所有文件 (*.*)"
        )
        
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                from extractor import LinkExtractor
                play_ids = LinkExtractor.extract_play_content(content)
                
                if not play_ids:
                    play_ids = [line.strip() for line in content.split('\n') if line.strip()]
                
                if play_ids:
                    self.add_tasks_from_play_ids(play_ids)
                else:
                    QMessageBox.warning(self, "警告", "文件中未找到有效的播放ID")
                    
            except Exception as e:
                QMessageBox.critical(self, "错误", f"读取文件失败: {e}")

    def add_tasks_from_play_ids(self, play_ids: list):
        urls = [self.config.PLAY_URL_TEMPLATE.format(pid) for pid in play_ids]
        
        album_name = self.current_album_name or "未知专辑"
        album_artist = self.current_album_artist or "未知艺术家"
        album_id = self.current_album_id or 0
        
        books = []
        for i, (pid, url) in enumerate(zip(play_ids, urls)):
            books.append({
                'album_id': album_id,
                'album_name': album_name,
                'album_artist': album_artist,
                'list_id': pid,
                'name': f"第{i+1}集",
                'url': url
            })
        
        result = self.manager.incremental_update(books)
        self.manager.save()
        
        self._refresh_album_list()
        self.refresh_display()
        
        QMessageBox.information(
            self, "完成",
            f"新增任务: {result['added_count']}, 重复: {result['duplicated_count']}"
        )

    def get_selected_tasks(self) -> list:
        selected = []
        for index in self.table_view.selectedIndexes():
            row = self.proxy_model.mapToSource(index).row()
            task = self.model.get_task(row)
            if task:
                selected.append(task)
        return selected

    def get_selected_list_ids(self) -> list:
        return [task.list_id for task in self.get_selected_tasks()]

    def parse_selected(self):
        selected = self.get_selected_tasks()
        if not selected:
            QMessageBox.information(self, "提示", "请先选择要解析的任务")
            return
        
        unparsed = [t for t in selected if not t.is_parsed]
        if not unparsed:
            QMessageBox.information(self, "提示", "选中的任务都已解析")
            return
        
        self._start_parse([t.url for t in unparsed], [t.list_id for t in unparsed])

    def parse_all_unparsed(self):
        if self.current_album_id is not None:
            unparsed = [t for t in self.manager.get_tasks_by_album(self.current_album_id) if not t.is_parsed]
        else:
            unparsed = self.manager.get_unparsed_books()
        
        if not unparsed:
            QMessageBox.information(self, "提示", "没有未解析的任务")
            return
        
        self._start_parse([t.url for t in unparsed], [t.list_id for t in unparsed])

    def _start_parse(self, urls: list, list_ids: list):
        self._set_buttons_enabled(False)
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(urls))
        self.progress_bar.setValue(0)
        self.status_label.setText("正在解析...")
        
        self.parse_list_ids = list_ids
        
        self.parse_thread = ParseThread(urls, list_ids, self.manager)
        self.parse_thread.progress.connect(self.on_parse_progress)
        self.parse_thread.finished.connect(self.on_parse_finished)
        self.parse_thread.error.connect(self.on_parse_error)
        self.parse_thread.start()

    def on_parse_progress(self, current: int, total: int, url: str):
        self.progress_bar.setValue(current)
        self.status_label.setText(f"正在解析 {current}/{total}")

    def on_parse_finished(self, audio_infos: list):
        self._set_buttons_enabled(True)
        self.progress_bar.setVisible(False)
        
        for audio_info in audio_infos:
            list_id = audio_info.get('list_id')
            if list_id:
                self.manager.update_parsed_status(list_id, True)
                self.manager.update_audio_url(list_id, audio_info.get('url', ''))
        
        self.manager.save()
        self.refresh_display()
        
        QMessageBox.information(
            self, "完成",
            f"解析完成，成功获取 {len(audio_infos)} 个音频信息"
        )

    def on_parse_error(self, error: str):
        self._set_buttons_enabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("")
        QMessageBox.warning(self, "错误", f"解析失败: {error}")

    def download_selected(self):
        selected = self.get_selected_tasks()
        if not selected:
            QMessageBox.information(self, "提示", "请先选择要下载的任务")
            return
        
        parsed = [t for t in selected if t.is_parsed]
        if not parsed:
            QMessageBox.information(self, "提示", "选中的任务都未解析，请先解析")
            return
        
        self._start_download(parsed)

    def download_all_undownloaded(self):
        if self.current_album_id is not None:
            undownloaded = [t for t in self.manager.get_tasks_by_album(self.current_album_id) if not t.is_downloaded]
        else:
            undownloaded = self.manager.get_undownloaded_books()
        
        if not undownloaded:
            QMessageBox.information(self, "提示", "没有未下载的任务")
            return
        
        self._start_download(undownloaded)

    def _start_download(self, tasks: list):
        audio_infos = []
        for task in tasks:
            audio_info = self.manager.get_audio_info(task.list_id)
            if audio_info:
                audio_info['list_id'] = task.list_id
                audio_infos.append(audio_info)
        
        if not audio_infos:
            QMessageBox.warning(self, "错误", "没有可下载的音频信息")
            return
        
        self._set_buttons_enabled(False)
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(audio_infos))
        self.progress_bar.setValue(0)
        self.status_label.setText("正在下载...")
        
        self.download_list_ids = [t.list_id for t in tasks]
        
        download_dir = self.config.DEFAULT_DOWNLOAD_DIR
        
        self.download_thread = DownloadThread(audio_infos, download_dir)
        self.download_thread.progress.connect(self.on_download_progress)
        self.download_thread.finished.connect(self.on_download_finished)
        self.download_thread.error.connect(self.on_download_error)
        self.download_thread.start()

    def on_download_progress(self, name: str, status: str):
        current = self.progress_bar.value()
        self.progress_bar.setValue(current + 1)
        self.status_label.setText(f"正在下载: {name[:30]}...")

    def on_download_finished(self, success_count: int, total: int):
        self._set_buttons_enabled(True)
        self.progress_bar.setVisible(False)
        
        for list_id in self.download_list_ids:
            self.manager.update_downloaded_status(list_id, True)
        
        self.manager.save()
        self.refresh_display()
        
        QMessageBox.information(
            self, "完成",
            f"下载完成: {success_count}/{total} 成功"
        )

    def on_download_error(self, error: str):
        self._set_buttons_enabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("")
        QMessageBox.warning(self, "错误", f"下载失败: {error}")

    def _set_buttons_enabled(self, enabled: bool):
        self.btn_search.setEnabled(enabled)
        self.btn_import.setEnabled(enabled)
        self.btn_parse.setEnabled(enabled)
        self.btn_parse_all.setEnabled(enabled)
        self.btn_download.setEnabled(enabled)
        self.btn_download_all.setEnabled(enabled)
        self.btn_clear.setEnabled(enabled)

    def clear_completed(self):
        if self.current_album_id is not None:
            completed = [t for t in self.manager.get_tasks_by_album(self.current_album_id) if t.is_downloaded]
        else:
            completed = [t for t in self.manager.tasks.values() if t.is_downloaded]
        
        if not completed:
            QMessageBox.information(self, "提示", "没有已完成的任务")
            return
        
        reply = QMessageBox.question(
            self, "确认",
            f"确定要清空 {len(completed)} 个已完成的任务吗?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            for task in completed:
                self.manager.remove_task(task.list_id)
            self.manager.save()
            self._refresh_album_list()
            self.refresh_display()

    def show_about(self):
        QMessageBox.about(
            self, "关于",
            "有声小说下载管理器 v1.0\n\n"
            "整合搜索、解析、下载功能\n"
            "统一使用PyQt6界面"
        )

    def closeEvent(self, event):
        if getattr(self, 'parse_thread', None) and self.parse_thread.isRunning():
            self.parse_thread.stop()
            self.parse_thread.wait(3000)
        if getattr(self, 'fetch_thread', None) and self.fetch_thread.isRunning():
            self.fetch_thread.terminate()
        self.manager.save()
        event.accept()


def main():
    warmup_requests()
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()