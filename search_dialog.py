import sys
import logging
import requests
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, 
    QListWidget, QListWidgetItem, QLabel, QWidget, QScrollArea,
    QFrame, QSplitter, QApplication
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QPalette, QColor, QIcon, QPixmap
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QUrl

from search_parser import SearchParser, SearchResult, SearchClient
from config import Config


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class ImageLoader(QThread):
    loaded = pyqtSignal(str, str)
    
    def __init__(self, url, reply_id):
        super().__init__()
        self.url = url
        self.reply_id = reply_id
    
    def run(self):
        try:
            response = requests.get(self.url, timeout=10)
            if response.status_code == 200:
                self.loaded.emit(self.reply_id, response.content)
        except:
            pass


class SearchThread(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, keyword):
        super().__init__()
        self.keyword = keyword
    
    def run(self):
        try:
            logger.info(f"开始搜索: {self.keyword}")
            
            client = SearchClient()
            logger.debug("SearchClient 初始化完成")
            
            results = client.search(self.keyword)
            logger.info(f"搜索完成，找到 {len(results)} 个结果")
            
            for i, r in enumerate(results):
                logger.debug(f"结果 {i+1}: ID={r.book_id}, Title={r.title}, Narrator={r.narrator}")
            
            self.finished.emit(results)
        except Exception as e:
            logger.error(f"搜索异常: {e}", exc_info=True)
            self.error.emit(str(e))


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
                background-color: #f0f0f0;
                border-radius: 6px;
                border: 1px solid #e0e0e0;
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
        title_label.setStyleSheet("color: #1a1a1a;")
        title_label.setMaximumWidth(350)
        title_label.setWordWrap(True)
        
        narrator_label = QLabel(f"演播：{self.result.narrator}")
        narrator_label.setFont(QFont("Microsoft YaHei", 9))
        narrator_label.setStyleSheet("color: #666666;")
        
        author_label = QLabel(f"作者：{self.result.author}")
        author_label.setFont(QFont("Microsoft YaHei", 9))
        author_label.setStyleSheet("color: #666666;")
        
        desc_label = QLabel(self.result.description[:60] + "..." if len(self.result.description) > 60 else self.result.description)
        desc_label.setFont(QFont("Microsoft YaHei", 8))
        desc_label.setStyleSheet("color: #999999;")
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
        id_label.setStyleSheet("color: #8e44ad; font-weight: bold;")
        
        layout.addWidget(id_label, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        
        self.setStyleSheet("""
            QWidget {
                background-color: white;
            }
            QWidget:hover {
                background-color: #f8f5ff;
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


class SearchDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.results = []
        self.search_thread = None
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("搜索有声小说")
        self.setMinimumSize(600, 500)
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QLineEdit {
                padding: 10px 15px;
                border: 2px solid #e0e0e0;
                border-radius: 25px;
                font-size: 14px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #8e44ad;
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
            QListWidget {
                border: none;
                background-color: white;
            }
            QListWidget::item {
                border-bottom: 1px solid #f0f0f0;
            }
            QListWidget::item:selected {
                background-color: #f8f5ff;
            }
            QLabel#title_label {
                font-size: 20px;
                font-weight: bold;
                color: white;
            }
            QLabel#result_count {
                color: #666666;
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
        
        search_btn = QPushButton("搜索")
        search_btn.setObjectName("search_btn")
        search_btn.setFixedSize(90, 45)
        search_btn.clicked.connect(self.do_search)
        
        search_layout.addWidget(self.search_input, 1)
        search_layout.addWidget(search_btn)
        
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
        self.status_label.setStyleSheet("color: #666666; padding: 10px;")
        main_layout.addWidget(self.status_label)
    
    def do_search(self):
        keyword = self.search_input.text().strip()
        if not keyword:
            self.status_label.setText("请输入搜索关键词")
            return
        
        self.status_label.setText("搜索中...")
        self.result_list.clear()
        self.results = []
        
        self.search_thread = SearchThread(keyword)
        self.search_thread.finished.connect(self.on_search_finished)
        self.search_thread.error.connect(self.on_search_error)
        self.search_thread.start()
    
    def on_search_finished(self, results):
        self.results = results
        self.status_label.setText("")
        
        if not results:
            self.result_count_label.setText("未找到相关结果")
            return
        
        self.result_count_label.setText(f"找到 {len(results)} 个结果")
        
        for result in results:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, result)
            
            widget = ResultItemWidget(result)
            item.setSizeHint(widget.sizeHint())
            
            self.result_list.addItem(item)
            self.result_list.setItemWidget(item, widget)
    
    def on_search_error(self, error_msg):
        self.status_label.setText(f"搜索失败: {error_msg}")
    
    def on_item_clicked(self, item):
        pass
    
    def on_item_double_clicked(self, item):
        result = item.data(Qt.ItemDataRole.UserRole)
        if result:
            self.selected_book_id = result.book_id
            self.accept()
    
    def get_selected_book_id(self):
        return getattr(self, 'selected_book_id', None)


def show_search_dialog(parent=None) -> str:
    dialog = SearchDialog(parent)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.get_selected_book_id()
    return None


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    dialog = SearchDialog()
    dialog.search_input.setText("异常生物见闻录")
    dialog.do_search()
    
    result = dialog.exec()
    if result == QDialog.DialogCode.Accepted:
        book_id = dialog.get_selected_book_id()
        if book_id:
            print(f"选择的书籍ID: {book_id}")
    
    sys.exit(0)