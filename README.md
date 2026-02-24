# Super Get

有前途的有声书下载工具，基于一个大胆的想法。

## 功能特性

- **搜索功能** - 搜索有声书和音频内容
- **批量解析** - 解析音频专辑和章节信息
- **多线程下载** - 支持高并发下载
- **任务管理** - 管理下载任务队列
- **图形界面** - 友好的PyQt6图形用户界面

## 环境要求

- Python 3.8+
- Windows/Linux/Mac OS

## 安装依赖

```bash
pip install -r requirements.txt
```

## 项目结构

```
SUPER GET/
├── main.py              # 程序入口
├── main_window.py       # 主窗口界面
├── config.py            # 配置文件管理
├── scraper.py           # 网页抓取模块
├── downloader.py        # 下载器模块
├── extractor.py         # 数据提取模块
├── search_parser.py     # 搜索解析模块
├── book_task_manager.py # 任务管理模块
├── gui.py               # GUI基础模块
├── book_task_gui.py     # 任务管理界面
├── search_dialog.py     # 搜索对话框
├── logger.py            # 日志模块
├── config.json          # 配置文件
├── requirements.txt     # 依赖列表
└── downloads/           # 下载目录
```

## 快速开始

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 运行程序：
```bash
python main.py
```

## 配置说明

配置文件 `config.json` 包含以下选项：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| base_url | 网站基础URL | https://i275.com |
| cookie | 认证Cookie | - |
| request_interval | 请求间隔(秒) | 0.1 |
| request_timeout | 请求超时(秒) | 10 |
| max_retries | 最大重试次数 | 3 |
| max_workers | 最大并发数 | 32 |
| download_timeout | 下载超时(秒) | 60 |
| default_download_dir | 默认下载目录 | downloads |

## 主要功能

### 搜索有声书
通过关键词搜索有声书内容，支持搜索结果预览和选择。

### 解析专辑
输入专辑URL或ID，解析专辑中的所有章节信息。

### 下载管理
- 支持多线程并发下载
- 显示下载进度
- 支持暂停/继续/取消下载任务
- 自动重试失败任务

### 任务管理
- 创建下载任务
- 批量添加任务
- 任务状态跟踪
- 任务历史记录

## 技术栈

- **GUI框架**: PyQt6
- **HTTP请求**: requests
- **HTML解析**: BeautifulSoup4
- **并发处理**: threading

## 注意事项

1. 请确保配置文件中包含有效的Cookie
2. 合理设置请求间隔，避免对服务器造成压力
3. 下载目录需要有写入权限

## 许可证

详见 LICENSE 页面