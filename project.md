# Super Get 项目规则

## 项目概述

Super Get 是一个有声书下载工具，支持搜索、解析、批量下载音频内容。

## 技术栈

- **GUI框架**: PyQt6 >= 6.0.0
- **HTTP请求**: requests >= 2.28.0
- **HTML解析**: BeautifulSoup4 >= 4.11.0
- **并发处理**: threading (内置)
- **Python版本**: Python 3.8+

## 项目结构

```
SUPER GET/
├── main.py                    # 程序入口
├── main_window.py             # 主窗口界面 (PyQt6)
├── gui.py                     # GUI基础模块 (Tkinter旧版)
├── config.py                  # 配置管理类 Config
├── scraper.py                 # 网页抓取模块
├── downloader.py              # 下载器模块
├── extractor.py               # 数据提取模块
├── search_parser.py           # 搜索解析模块
├── book_task_manager.py       # 任务管理模块
├── book_task_gui.py           # 任务管理界面
├── search_dialog.py           # 搜索对话框
├── book_scraper.py            # 书籍页面抓取
├── logger.py                  # 日志模块
├── config.json                # 配置文件
├── requirements.txt           # 依赖列表
└── downloads/                 # 下载目录
```

---

## 核心模块详解

### 1. config.py - Config 类

**功能**: 配置文件管理，单例模式

**属性**:
| 属性名 | 类型 | 说明 |
|--------|------|------|
| BASE_URL | str | 网站基础URL (默认: https://i275.com) |
| PLAY_URL_TEMPLATE | str | 播放页面URL模板 |
| COOKIE | str | 认证Cookie |
| REQUEST_INTERVAL | float | 请求间隔(秒) |
| REQUEST_TIMEOUT | int | 请求超时(秒) |
| MAX_RETRIES | int | 最大重试次数 |
| MAX_WORKERS | int | 最大并发数 |
| DOWNLOAD_TIMEOUT | int | 下载超时(秒) |
| DEFAULT_DOWNLOAD_DIR | str | 默认下载目录 |
| JSON_OUTPUT_FILE | str | JSON输出文件名 |
| DEBUG | bool | 调试模式开关 |

**方法**:
| 方法名 | 参数 | 返回值 | 功能说明 |
|--------|------|--------|----------|
| get_headers() | - | dict | 获取HTTP请求头，包含User-Agent和Cookie |
| get_all_config() | - | dict | 获取所有配置 |
| update_config(key, value) | str, 任意 | None | 更新单个配置并保存 |
| update_multiple(updates) | dict | None | 批量更新配置 |
| reload() | - | None | 重新加载配置文件 |
| save() | - | None | 保存当前配置 |

---

### 2. scraper.py - AudioScraper 类

**功能**: 网页抓取，从播放页面提取音频URL信息

**方法**:
| 方法名 | 参数 | 返回值 | 功能说明 |
|--------|------|--------|----------|
| __init__(request_interval) | float | - | 初始化抓取器 |
| init_session() | - | bool | 初始化HTTP会话 |
| process_urls(urls) | List[str] | List[Dict] | 批量处理URL列表，提取音频信息 |
| extract_audio_info(url) | str | Optional[Dict] | 从单个URL提取音频信息 |
| extract_audio_from_html(html) | str | Optional[Dict] | 从HTML内容提取音频配置 |
| _extract_from_script(content) | str | Optional[Dict] | 从script标签提取音频配置 |
| save_to_json(audio_infos, filename) | list, str | bool | 保存音频信息到JSON文件 |
| load_from_json(filename) | str | Optional[List[Dict]] | 从JSON文件加载音频信息 |

**返回数据格式**:
```python
{
    'name': str,      # 音频名称
    'artist': str,    # 艺术家/作者
    'url': str,       # 音频URL
    'album': str      # 专辑名称 (可选)
}
```

---

### 3. downloader.py - 核心类

#### 3.1 AudioInfo (数据类)

**功能**: 音频信息数据容器

**属性**:
| 属性名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| name | str | - | 音频名称 |
| artist | str | - | 艺术家 |
| url | str | - | 音频URL |
| album | str | "" | 专辑名称 |
| file_path | str | "" | 文件保存路径 |
| download_status | str | "pending" | 下载状态 |
| retry_count | int | 0 | 重试次数 |
| error_message | str | "" | 错误信息 |
| list_id | int | 0 | 章节ID |

**下载状态枚举**: `pending`, `downloading`, `success`, `failed`, `expired`

**方法**:
| 方法名 | 参数 | 返回值 | 功能说明 |
|--------|------|--------|----------|
| generate_file_path(base_dir) | str | None | 生成文件保存路径，按"专辑名 - 艺术家"目录结构 |
| sanitize_filename(filename) | str | str | 清理文件名中的非法字符 |
| get_file_extension() | - | str | 从URL获取文件扩展名 |

#### 3.2 DownloadWorker (线程类)

**功能**: 下载工作线程，从队列获取任务并执行下载

**构造参数**:
| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| work_queue | queue.Queue | - | 任务队列 |
| result_queue | queue.Queue | - | 结果队列 |
| max_retries | int | 3 | 最大重试次数 |
| timeout | int | 60 | 超时时间(秒) |

**方法**:
| 方法名 | 参数 | 返回值 | 功能说明 |
|--------|------|--------|----------|
| run() | - | - | 线程主循环，从队列获取任务并下载 |
| stop() | - | None | 停止工作线程 |
| download_with_retry(audio_info) | AudioInfo | bool | 带重试的下载 |
| download_file(audio_info) | AudioInfo | bool | 执行文件下载 |
| _download_core(...) | - | bool | 核心下载逻辑，支持进度回调 |

#### 3.3 AudioDownloader (主下载器类)

**功能**: 多线程下载管理器，协调多个下载工作线程

**构造参数**:
| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| max_workers | int | None | 最大工作线程数 |
| max_retries | int | None | 最大重试次数 |
| download_dir | str | None | 下载目录 |

**方法**:
| 方法名 | 参数 | 返回值 | 功能说明 |
|--------|------|--------|----------|
| load_from_json(json_file) | str | List[AudioInfo] | 从JSON加载音频信息列表 |
| prepare_tasks(audio_infos) | List[AudioInfo] | None | 准备下载任务，加入队列 |
| start_workers() | - | None | 启动指定数量的工作线程 |
| monitor_progress() | - | None | 监控下载进度并输出日志 |
| download(json_file) | str | bool | 执行完整下载流程 |
| download_with_callback(audio_infos, callback) | list, function | bool | 带进度回调的下载 |
| save_results(audio_infos) | List[AudioInfo] | None | 保存下载结果到文件 |

---

### 4. extractor.py - LinkExtractor 类

**功能**: 从文本和HTML中提取播放链接和章节信息

**方法**:
| 方法名 | 参数 | 返回值 | 功能说明 |
|--------|------|--------|----------|
| extract_play_content(text) | str | List[str] | 从文本中提取播放ID列表 |
| extract_with_context(text, context_chars) | str, int | List[Dict] | 提取播放ID及上下文 |
| extract_chapters(text) | str | List[ChapterInfo] | 从HTML提取章节列表 |
| extract_chapters_as_dict(text) | str | List[Dict] | 提取章节并转为字典 |
| build_play_urls(play_ids) | List[str] | List[str] | 构建完整播放URL列表 |
| extract_from_file(input_file, output_file) | str, str | List[str] | 从文件提取播放ID |

#### ChapterInfo (数据类)

**属性**: chapter_id, index, title, href

---

### 5. search_parser.py - 搜索模块

#### SearchResult (数据类)

**功能**: 搜索结果数据容器

**属性**: book_id, title, author, narrator, cover_url, description, url

#### SearchParser 类

**功能**: 解析搜索结果页面

**方法**:
| 方法名 | 参数 | 返回值 | 功能说明 |
|--------|------|--------|----------|
| build_search_url(keyword) | str | str | 构建搜索URL |
| parse_search_results(html) | str | List[SearchResult] | 解析搜索结果HTML |
| get_search_result_count(html) | str | int | 获取搜索结果数量 |

#### SearchClient 类

**功能**: 搜索客户端，负责网络请求

**方法**:
| 方法名 | 参数 | 返回值 | 功能说明 |
|--------|------|--------|----------|
| init_session() | - | None | 初始化HTTP会话 |
| search(keyword) | str | List[SearchResult] | 执行搜索 |
| search_from_file(file_path) | str | List[SearchResult] | 从文件解析搜索结果 |

---

### 6. book_task_manager.py - 任务管理模块

#### BookTask (数据类)

**功能**: 下载任务数据容器

**属性**:
| 属性名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| album_id | int | - | 专辑ID |
| album_name | str | - | 专辑名称 |
| album_artist | str | - | 艺术家/演播 |
| list_id | int | - | 章节ID |
| name | str | - | 章节名称 |
| url | str | - | 播放页面URL |
| is_parsed | bool | False | 是否已解析 |
| is_downloaded | bool | False | 是否已下载 |
| audio_url | str | "" | 音频URL |
| added_time | str | 当前时间 | 添加时间 |
| parsed_time | str | "" | 解析时间 |
| downloaded_time | str | "" | 下载时间 |

**方法**:
| 方法名 | 参数 | 返回值 | 功能说明 |
|--------|------|--------|----------|
| to_dict() | - | Dict | 转换为字典 |
| from_dict(data) | Dict | BookTask | 从字典创建 |

#### BookTaskManager 类

**功能**: 任务管理器，负责任务的增删改查和持久化

**方法**:
| 方法名 | 参数 | 返回值 | 功能说明 |
|--------|------|--------|----------|
| add_task(...) | 多个 | bool | 添加单个任务 |
| add_tasks_batch(books) | List[Dict] | int | 批量添加任务 |
| incremental_update(books) | List[Dict] | Dict | 增量更新，返回添加/重复数量 |
| get_unparsed_books() | - | List[BookTask] | 获取未解析任务 |
| get_undownloaded_books() | - | List[BookTask] | 获取未下载任务 |
| get_tasks_by_album(album_id) | int | List[BookTask] | 按专辑获取任务 |
| get_all_tasks() | - | List[BookTask] | 获取所有任务 |
| update_parsed_status(list_id, is_parsed) | int, bool | bool | 更新解析状态 |
| update_downloaded_status(list_id, is_downloaded) | int, bool | bool | 更新下载状态 |
| update_audio_url(list_id, audio_url) | int, str | bool | 更新音频URL |
| reset_parsed_status(list_id) | int | bool | 重置解析状态 |
| reset_all_download_status() | - | int | 重置所有下载状态 |
| remove_task(list_id) | int | bool | 删除任务 |
| save() | - | bool | 保存任务到JSON文件 |
| load() | - | tuple | 加载任务文件，返回(成功与否, 原因) |
| get_statistics() | - | Dict | 获取统计信息 |

---

### 7. main_window.py - GUI核心模块

#### 线程类 (QThread)

| 类名 | 信号 | 功能说明 |
|------|------|----------|
| SearchThread | finished(list), error(str) | 后台搜索 |
| ParseThread | progress(int, int, str), finished(list), error(str) | 后台解析URL |
| FetchChapterListThread | finished(list), error(str) | 获取章节列表 |
| ParseAlbumThread | progress, finished, error, saved | 解析整个专辑 |
| DownloadThread | progress, finished, error | 后台下载 |

#### UI组件类

| 类名 | 继承 | 功能说明 |
|------|------|----------|
| NaturalSortProxyModel | QSortFilterProxyModel | 自然排序代理模型 |
| BookTaskTableModel | QAbstractTableModel | 任务表格数据模型 |
| AlbumListWidget | QWidget | 左侧专辑列表组件 |
| ResultItemWidget | QWidget | 搜索结果项组件 |
| SearchResultDialog | QDialog | 搜索结果对话框 |
| EditAlbumDialog | QDialog | 编辑专辑元数据对话框 |
| EditTaskDialog | QDialog | 编辑任务对话框 |
| MainWindow | QMainWindow | 主窗口 |

#### MainWindow 主要方法

| 方法名 | 功能说明 |
|--------|----------|
| init_ui() | 初始化UI界面 |
| load_data() | 加载任务数据 |
| refresh_display() | 刷新任务显示 |
| show_search_dialog() | 显示搜索对话框 |
| add_book_from_search(book) | 从搜索结果添加书籍 |
| parse_selected() | 解析选中的任务 |
| download_selected() | 下载选中的任务 |
| delete_selected() | 删除选中的任务 |
| clear_completed() | 清空已完成任务 |
| open_log_folder() | 打开日志文件夹 |
| open_download_folder() | 打开下载文件夹 |

---

### 8. book_scraper.py

**功能**: 书籍页面抓取，获取专辑的章节列表HTML

**方法**:
| 方法名 | 参数 | 返回值 | 功能说明 |
|--------|------|--------|----------|
| download_book_page(book_id) | int | str | 下载书籍页面HTML |

---

### 9. logger.py - 日志模块

**功能**: 统一的日志记录和崩溃捕获

**方法**:
| 方法名 | 参数 | 返回值 | 功能说明 |
|--------|------|--------|----------|
| setup_logger(name) | str | logging.Logger | 创建并配置日志器 |
| get_logger(name) | str | logging.Logger | 获取日志器 |
| log_crash(type, value, traceback) | - | None | 记录崩溃信息到文件 |

---

### 10. gui.py - Tkinter旧版GUI (了解即可)

包含 TaskManager 和 App 类，已被 PyQt6 版本取代。

---

## 文件依赖关系

```
main.py
  └── main_window.py
        ├── config.py (Config)
        ├── logger.py
        ├── book_task_manager.py (BookTaskManager, BookTask)
        ├── search_parser.py (SearchClient, SearchResult)
        ├── scraper.py (AudioScraper)
        ├── downloader.py (AudioDownloader, AudioInfo)
        ├── book_scraper.py
        └── extractor.py (LinkExtractor, ChapterInfo)
```

## 关键流程

1. **搜索添加**: SearchThread → SearchClient → 搜索结果 → 添加BookTask
2. **解析URL**: ParseThread → AudioScraper.extract_audio_info() → 更新audio_url
3. **下载音频**: DownloadThread → AudioDownloader → 多线程DownloadWorker → 文件下载
4. **任务持久化**: BookTaskManager.save() / load() → config/tasks.json
