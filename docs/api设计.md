# 365听书 API 设计文档

## 概述
- **框架**: FastAPI
- **功能**: 为 Vue3 前端提供 REST API
- **初始化方式**: `FastAPI(manager=manager对象)`

## API 端点设计

### 1. 搜索相关

#### GET /api/search
搜索书籍

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| q | string | 是 | 搜索关键词 |

**响应**:
```json
[
  {
    "id": 12345,
    "bookTitle": "书名",
    "bookDesc": "简介",
    "bookImage": "图片URL",
    "bookAnchor": "anchor",
    "count": 100,
    "updateStatus": 1,
    "heat": 0
  }
]
```

---

### 2. 书籍管理

#### GET /api/books
获取我的书籍列表

**响应**:
```json
[
  {
    "id": 12345,
    "count": 100,
    "updateStatus": 1,
    "image": "图片URL",
    "desc": "简介",
    "title": "书名",
    "anchor": "anchor"
  }
]
```

#### POST /api/book/add
添加书籍（根据ID自动获取完整信息）

**请求体**:
```json
{
  "id": 12345
}
```

**响应**:
```json
{"message": "添加成功"}
```

#### DELETE /api/book/{book_id}
删除书籍

**响应**:
```json
{"message": "删除成功"}
```

#### GET /api/book/{book_id}
获取书籍详情

**响应**:
```json
{
  "id": 12345,
  "count": 100,
  "updateStatus": 1,
  "image": "图片URL",
  "desc": "简介",
  "title": "书名",
  "anchor": "anchor"
}
```

#### GET /api/book/{book_id}/chapters
获取书籍章节列表

**响应**:
```json
[
  {"chapterid": 1, "position": 1, "title": "第1章", "downloaded": true},
  {"chapterid": 2, "position": 2, "title": "第2章", "downloaded": false}
]
```

#### POST /api/book/{book_id}/chapters
更新书籍章节列表

**响应**:
```json
{"message": "已更新章节列表"} //注意，不支持查询具体更新了多少
```

---

### 3. 下载管理

#### POST /api/download/start
开始下载

**请求体** (可选):
```json
{
  "book_id": 12345,        // 书籍ID，不传则下载所有书籍
  "chapter_ids": [1, 2]   // 章节ID列表，不传则下载该书籍所有未下载章节
}
```

**响应**:
```json
{"message": "开始下载"}
```

#### POST /api/download/pause
暂停下载

**请求体** (可选):
```json
{
  "book_id": 12345,        // 书籍ID，不传则暂停所有
  "chapter_ids": [1, 2]   // 章节ID列表
}
```

**响应**:
```json
{"message": "已暂停"}
```

#### POST /api/download/resume
继续下载

**请求体** (可选):
```json
{
  "book_id": 12345,        // 书籍ID，不传则继续所有
  "chapter_ids": [1, 2]    // 章节ID列表
}
```

**响应**:
```json
{"message": "已继续"}
```

#### POST /api/download/cancel
取消下载

**请求体** (可选):
```json
{
  "book_id": 12345,        // 书籍ID，不传则取消所有
  "chapter_ids": [1, 2]    // 章节ID列表
}
```

**响应**:
```json
{"message": "已取消"}
```

#### GET /api/download/status
获取下载状态

**响应**:
```json
{
  "total": 100,
  "pending": 50,
  "downloading": 4,
  "paused": 0,
  "completed": 46,
  "failed": 0,
  "is_running": true,
  "is_paused": false
}
```

---

### 4. 定时任务

#### POST /api/timer/start
启动定时同步任务

**请求体** (可选):
```json
{
  "interval_hours": 1.0  // 不传则使用配置文件的默认值
}
```

**响应**:
```json
{"message": "定时任务已启动"}
```

#### POST /api/timer/stop
停止定时同步任务

**响应**:
```json
{"message": "定时任务已停止"}
```

#### POST /api/timer/book/add
添加书籍到定时任务

**请求体**:
```json
{
  "book_id": 12345
}
```

**响应**:
```json
{"message": "已添加到定时任务"}
```

#### POST /api/timer/book/remove
从定时任务移除书籍

**请求体**:
```json
{
  "book_id": 12345
}
```

**响应**:
```json
{"message": "已从定时任务移除"}
```

#### GET /api/timer/status
获取定时任务状态

**响应**:
```json
{
  "is_running": true,
  "interval_hours": 1.0,
  "book_ids": [12345, 67890]
}
```

---

## 初始化方式

```python
from fastapi import FastAPI
from module.manager import Manager
from module.logger import get_logger
from module.config import Config

logger = get_logger('API', {'console': {'enabled': True, 'level': 'INFO'}})
config = Config()
manager = Manager(logger=logger, config=config)

app = FastAPI(manager=manager)
```

## 错误处理

- 404: 资源不存在
- 400: 请求参数错误
- 500: 服务器内部错误
