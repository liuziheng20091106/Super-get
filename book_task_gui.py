import sys
import json
import time
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTableView, QHeaderView, QCheckBox, QPushButton,
    QMenu, QDialog, QLineEdit, QTextEdit, QGroupBox, QScrollArea,
    QMessageBox, QInputDialog, QAbstractItemView
)
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel, pyqtSignal, QObject, QThread
from PyQt6.QtGui import QAction, QContextMenuEvent, QFont, QColor, QPalette
from book_task_manager import BookTaskManager, BookTask


class BookTaskTableModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tasks = []
        self.headers = ['序号', '名称', '解析状态', '下载状态']

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
                return "是" if task.is_parsed else "否"
            elif col == 3:
                return "是" if task.is_downloaded else "否"
        elif role == Qt.ItemDataRole.BackgroundRole:
            if task.is_downloaded:
                return QColor(220, 255, 220)
            elif task.is_parsed:
                return QColor(255, 255, 220)
        elif role == Qt.ItemDataRole.ToolTipRole:
            return self._build_tooltip(task)

        return None

    def _build_tooltip(self, task: BookTask) -> str:
        return (f"专辑名: {task.album_name}\n"
                f"专辑ID: {task.album_id}\n"
                f"专辑艺术家: {task.album_artist}\n"
                f"列表ID: {task.list_id}\n"
                f"名称: {task.name}\n"
                f"URL: {task.url}\n"
                f"解析状态: {'是' if task.is_parsed else '否'}\n"
                f"下载状态: {'是' if task.is_downloaded else '否'}\n"
                f"添加时间: {task.added_time}\n"
                f"解析时间: {task.parsed_time or '未解析'}\n"
                f"下载时间: {task.downloaded_time or '未下载'}")

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


class Worker(QThread):
    finished = pyqtSignal()
    progress = pyqtSignal(int, str)
    error = pyqtSignal(str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            self.func(*self.args, **self.kwargs)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))


class BookTaskGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.manager = BookTaskManager()
        self.current_album_id = None
        self.current_album_name = ""
        self.current_album_artist = ""
        self.worker = None
        self.selected_rows = set()
        self.init_ui()
        self.load_data()

    def init_ui(self):
        self.setWindowTitle("书籍解析管理")
        self.setGeometry(100, 100, 1000, 700)
        self.setMinimumSize(800, 500)

        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(250, 250, 250))
        self.setPalette(palette)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        main_layout.addWidget(self._create_album_info_group())
        main_layout.addWidget(self._create_button_group())
        main_layout.addWidget(self._create_table_group())

        self._apply_styles()

    def _create_album_info_group(self) -> QGroupBox:
        group = QGroupBox("专辑信息")
        layout = QVBoxLayout()

        info_layout = QHBoxLayout()
        info_layout.setSpacing(20)

        self.album_name_label = QLabel("专辑名: 未加载")
        self.album_id_label = QLabel("专辑ID: -")
        self.album_artist_label = QLabel("艺术家: -")
        self.task_count_label = QLabel("任务数: 0")

        for label in [self.album_name_label, self.album_id_label, 
                      self.album_artist_label, self.task_count_label]:
            label.setStyleSheet("font-size: 14px; padding: 5px;")
            info_layout.addWidget(label)

        info_layout.addStretch()

        layout.addLayout(info_layout)
        group.setLayout(layout)
        return group

    def _create_button_group(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        btn_style = "QPushButton { padding: 8px 16px; border-radius: 4px; background-color: #4CAF50; color: white; border: none; } QPushButton:hover { background-color: #45a049; } QPushButton:pressed { background-color: #3d8b40; }"

        self.btn_process_selected = QPushButton("处理选中未解析部分")
        self.btn_process_selected.setStyleSheet(btn_style)
        self.btn_process_selected.clicked.connect(self.process_selected_unparsed)
        layout.addWidget(self.btn_process_selected)

        self.btn_submit_selected = QPushButton("提交选中的下载任务")
        self.btn_submit_selected.setStyleSheet(btn_style)
        self.btn_submit_selected.clicked.connect(self.submit_selected_download)
        layout.addWidget(self.btn_submit_selected)

        layout.addSpacing(20)

        self.btn_process_all = QPushButton("处理全部未解析部分")
        self.btn_process_all.setStyleSheet(btn_style)
        self.btn_process_all.clicked.connect(self.process_all_unparsed)
        layout.addWidget(self.btn_process_all)

        self.btn_incremental = QPushButton("增量更新专辑信息")
        self.btn_incremental.setStyleSheet(btn_style)
        self.btn_incremental.clicked.connect(self.incremental_update)
        layout.addWidget(self.btn_incremental)

        self.btn_submit_all = QPushButton("提交全部未下载任务")
        self.btn_submit_all.setStyleSheet(btn_style)
        self.btn_submit_all.clicked.connect(self.submit_all_undownloaded)
        layout.addWidget(self.btn_submit_all)

        layout.addStretch()

        widget.setLayout(layout)
        return widget

    def _create_table_group(self) -> QWidget:
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

        self.table_view.setColumnWidth(0, 60)
        self.table_view.setColumnWidth(2, 80)
        self.table_view.setColumnWidth(3, 80)

        self.table_view.clicked.connect(self.on_row_clicked)
        self.table_view.pressed.connect(self.on_row_pressed)

        layout.addWidget(self.table_view)
        widget.setLayout(layout)
        return widget

    def _apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #fafafa;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QTableView {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                gridline-color: #e0e0e0;
            }
            QTableView::item {
                padding: 5px;
            }
            QTableView::item:selected {
                background-color: #2196F3;
                color: white;
            }
            QTableView::item:hover {
                background-color: #E3F2FD;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 8px;
                border: none;
                border-right: 1px solid #e0e0e0;
                border-bottom: 1px solid #e0e0e0;
                font-weight: bold;
            }
            QPushButton {
                padding: 8px 16px;
                border-radius: 4px;
                background-color: #4CAF50;
                color: white;
                border: none;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
            QLabel {
                color: #333333;
            }
        """)

    def load_data(self):
        if self.manager.load():
            self.refresh_display()

    def refresh_display(self):
        tasks = self.manager.get_all_tasks()
        self.model.set_tasks(tasks)
        self._update_album_info()
        self._update_task_count()

    def _update_album_info(self):
        if self.current_album_name:
            self.album_name_label.setText(f"专辑名: {self.current_album_name}")
            self.album_id_label.setText(f"专辑ID: {self.current_album_id}")
            self.album_artist_label.setText(f"艺术家: {self.current_album_artist}")
        else:
            if self.manager.tasks:
                first_task = next(iter(self.manager.tasks.values()))
                self.current_album_id = first_task.album_id
                self.current_album_name = first_task.album_name
                self.current_album_artist = first_task.album_artist
                self.album_name_label.setText(f"专辑名: {self.current_album_name}")
                self.album_id_label.setText(f"专辑ID: {self.current_album_id}")
                self.album_artist_label.setText(f"艺术家: {self.current_album_artist}")

    def _update_task_count(self):
        stats = self.manager.get_statistics()
        self.task_count_label.setText(
            f"任务数: {stats['total']} | 已解析: {stats['parsed']} | 已下载: {stats['downloaded']}"
        )

    def set_album_info(self, album_id: int, album_name: str, album_artist: str):
        self.current_album_id = album_id
        self.current_album_name = album_name
        self.current_album_artist = album_artist
        self.album_name_label.setText(f"专辑名: {album_name}")
        self.album_id_label.setText(f"专辑ID: {album_id}")
        self.album_artist_label.setText(f"艺术家: {album_artist}")

    def add_books(self, books: list):
        result = self.manager.incremental_update(books)
        self.refresh_display()
        return result

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

    def on_row_clicked(self, index):
        pass

    def on_row_pressed(self, index):
        if index.button() == Qt.MouseButton.RightButton:
            self.show_context_menu(index)

    def show_context_menu(self, index):
        row = self.proxy_model.mapToSource(index).row()
        task = self.model.get_task(row)
        if not task:
            return

        menu = QMenu(self)

        action_copy_id = QAction("复制ID", self)
        action_copy_id.triggered.connect(lambda: self._copy_to_clipboard(str(task.list_id)))
        menu.addAction(action_copy_id)

        action_copy_name = QAction("复制名称", self)
        action_copy_name.triggered.connect(lambda: self._copy_to_clipboard(task.name))
        menu.addAction(action_copy_name)

        menu.addSeparator()

        action_rename = QAction("重命名", self)
        action_rename.triggered.connect(lambda: self._rename_task(row))
        menu.addAction(action_rename)

        action_edit_index = QAction("修改序号", self)
        action_edit_index.triggered.connect(lambda: self._edit_index(row))
        menu.addAction(action_edit_index)

        menu.addSeparator()

        action_download = QAction("下载", self)
        action_download.triggered.connect(lambda: self._download_task(row))
        menu.addAction(action_download)

        action_parse = QAction("解析或重新解析", self)
        action_parse.triggered.connect(lambda: self._parse_task(row))
        menu.addAction(action_parse)

        menu.exec(self.table_view.viewport().mapToGlobal(index.rect().topLeft()))

    def _copy_to_clipboard(self, text: str):
        clipboard = QApplication.clipboard()
        clipboard.setText(text)

    def _rename_task(self, row: int):
        task = self.model.get_task(row)
        if not task:
            return

        new_name, ok = QInputDialog.getText(self, "重命名", "请输入新名称:", text=task.name)
        if ok and new_name:
            task.name = new_name
            self.model.update_task(row)
            self.manager.save()

    def _edit_index(self, row: int):
        task = self.model.get_task(row)
        if not task:
            return

        new_index, ok = QInputDialog.getInt(self, "修改序号", "请输入新序号:", value=row + 1, min=1)
        if ok:
            old_row = row
            new_row = new_index - 1

            if 0 <= new_row < len(self.model.tasks):
                self.model.beginResetModel()
                task = self.model.tasks.pop(old_row)
                self.model.tasks.insert(new_row, task)
                self.model.endResetModel()
                self.manager.save()

    def _download_task(self, row: int):
        task = self.model.get_task(row)
        if task:
            self._submit_download([task.list_id])

    def _parse_task(self, row: int):
        task = self.model.get_task(row)
        if task:
            self._process_parse([task.list_id])

    def process_selected_unparsed(self):
        selected = self.get_selected_tasks()
        unparsed = [t for t in selected if not t.is_parsed]
        if not unparsed:
            QMessageBox.information(self, "提示", "选中的项目都已解析")
            return
        self._process_parse([t.list_id for t in unparsed])

    def submit_selected_download(self):
        selected = self.get_selected_list_ids()
        if not selected:
            QMessageBox.information(self, "提示", "请先选择要下载的项目")
            return
        self._submit_download(selected)

    def process_all_unparsed(self):
        unparsed = self.manager.get_unparsed_books()
        if not unparsed:
            QMessageBox.information(self, "提示", "没有未解析的项目")
            return
        self._process_parse([t.list_id for t in unparsed])

    def incremental_update(self):
        QMessageBox.information(self, "提示", "请在子类中实现增量更新逻辑")

    def submit_all_undownloaded(self):
        undownloaded = self.manager.get_undownloaded_books()
        if not undownloaded:
            QMessageBox.information(self, "提示", "没有未下载的项目")
            return
        self._submit_download([t.list_id for t in undownloaded])

    def _process_parse(self, list_ids: list):
        QMessageBox.information(self, "解析", f"开始解析 {len(list_ids)} 个项目\n请在子类中实现具体解析逻辑")

    def _submit_download(self, list_ids: list):
        QMessageBox.information(self, "下载", f"提交 {len(list_ids)} 个下载任务\n请在子类中实现具体下载逻辑")

    def closeEvent(self, event):
        self.manager.save()
        event.accept()


class BookTaskManagerWindow(BookTaskGUI):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("书籍解析管理器")

    def incremental_update(self):
        text, ok = QInputDialog.getText(self, "增量更新", "请输入书籍信息 (JSON格式列表):")
        if ok and text:
            try:
                books = json.loads(text)
                result = self.add_books(books)
                QMessageBox.information(
                    self, "完成",
                    f"新增: {result['added_count']}, 重复: {result['duplicated_count']}"
                )
            except json.JSONDecodeError:
                QMessageBox.warning(self, "错误", "JSON格式不正确")

    def _process_parse(self, list_ids: list):
        from scraper import AudioScraper
        from config import Config

        urls = []
        for lid in list_ids:
            task = self.manager.get_task(lid)
            if task:
                urls.append(task.url)

        if not urls:
            return

        self.btn_process_all.setEnabled(False)
        self.btn_process_selected.setEnabled(False)

        def parse_worker():
            scraper = AudioScraper()
            scraper.init_session()
            audio_infos = scraper.process_urls(urls)

            for lid in list_ids:
                self.manager.update_parsed_status(lid, True)

            self.manager.save()

        self.worker = Worker(parse_worker)
        self.worker.finished.connect(self._on_parse_finished)
        self.worker.error.connect(self._on_worker_error)
        self.worker.start()

    def _on_parse_finished(self):
        self.btn_process_all.setEnabled(True)
        self.btn_process_selected.setEnabled(True)
        self.refresh_display()
        QMessageBox.information(self, "完成", "解析任务已完成")

    def _on_worker_error(self, error: str):
        self.btn_process_all.setEnabled(True)
        self.btn_process_selected.setEnabled(True)
        QMessageBox.warning(self, "错误", f"解析失败: {error}")

    def _submit_download(self, list_ids: list):
        from downloader import AudioDownloader
        from config import Config

        tasks = [self.manager.get_task(lid) for lid in list_ids if self.manager.get_task(lid)]
        audio_infos = []
        for task in tasks:
            if task.is_parsed:
                audio_infos.append({
                    'name': task.name,
                    'artist': task.album_artist,
                    'url': task.url
                })

        if not audio_infos:
            QMessageBox.information(self, "提示", "没有可下载的已解析项目")
            return

        self.btn_submit_all.setEnabled(False)
        self.btn_submit_selected.setEnabled(False)

        def download_worker():
            downloader = AudioDownloader(
                max_workers=Config.MAX_WORKERS,
                max_retries=Config.MAX_RETRIES,
                download_dir=Config.DEFAULT_DOWNLOAD_DIR
            )
            downloader.download()

            for lid in list_ids:
                self.manager.update_downloaded_status(lid, True)

            self.manager.save()

        self.worker = Worker(download_worker)
        self.worker.finished.connect(self._on_download_finished)
        self.worker.error.connect(self._on_worker_error)
        self.worker.start()

    def _on_download_finished(self):
        self.btn_submit_all.setEnabled(True)
        self.btn_submit_selected.setEnabled(True)
        self.refresh_display()
        QMessageBox.information(self, "完成", "下载任务已完成")


def main():
    app = QApplication(sys.argv)
    window = BookTaskManagerWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()