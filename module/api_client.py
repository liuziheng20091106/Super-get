"""
365听书 API 客户端
基于 365ting 生成的API调用函数
"""
import hashlib
import time
import requests
from typing import Optional, Dict, Any, Union

from module.data_provider import BookInfo, ChapterInfo, SearchResult
from module import old_chapter_url_api


CONFIG_URL = "http://101.43.48.231:8090"

HEADERS = {
    "User-Agent": "TingShiJie/1.8.8 (m.i275.com)",
    "Connection": "keep-alive",
    "Accept": "*/*",
    "Accept-Encoding": "gzip",
}

DEFAULT_TIMEOUT = 10


def get_add_it_parapet(timestamp: str) -> str:
    """
    生成签名
    :param timestamp: 时间戳字符串
    :return: 两次 MD5 后的签名串
    """
    secret_key = "J9gSpfUlzYxE8Hn5IXiGaD2jVMrwAm0K"
    concat = timestamp + secret_key
    md5_1 = hashlib.md5(concat.encode('utf-8')).hexdigest()
    second_concat = md5_1 + secret_key
    md5_2 = hashlib.md5(second_concat.encode('utf-8')).hexdigest()
    return md5_2


def get_chapter_list(baseurl: str, book_id: int, size: int = 100000, logger=None, request_timeout: int = DEFAULT_TIMEOUT) -> Union[list[ChapterInfo], bool]:
    """
    获取书籍章节列表

    Args:
        baseurl: API基础URL，如 https://app.365ting.com/listen/Apitzg2025/
        book_id: 书籍ID
        size: 返回数量限制
        logger: 日志记录器
        request_timeout: 请求超时时间（秒）

    Returns:
        ChapterInfo列表，失败返回False
    """
    try:
        url = f"{baseurl}chapter"
        params = {
            "size": size,
            "bookId": book_id
        }
        if logger:
            logger.info(f"[获取章节列表] 书籍ID: {book_id}, URL: {url}")
        response = requests.get(url, params=params, headers=HEADERS, timeout=request_timeout)
        response.raise_for_status()
        data = response.json()

        if data.get("status") != 0:
            raise ValueError(f"API返回错误: {data.get('message', '未知错误')}, 书籍ID: {book_id}")

        chapter_list = data.get("data", {}).get("list", [])
        if not chapter_list:
            raise ValueError(f"未找到章节列表, 书籍ID: {book_id}")

        chapters = []
        for item in chapter_list:
            if "chapterId" not in item or "bookId" not in item:
                raise ValueError(f"章节数据缺少chapterId或bookId: {item}")

            chapter = ChapterInfo(
                chapterid=item.get("chapterId", 0),
                position=item.get("position", 0),
                title=item.get("title", ""),
                time=item.get("time", ""),
                uploadDate=item.get("uploadDate", ""),
                url=item.get("url", 0),
                bookTitle=item.get("bookTitle", ""),
                bookid=item.get("bookId", 0),
                bookAnchor=item.get("bookHost", ""),
                bookDesc=item.get("bookDesc", ""),
                bookImage=item.get("bookImage", "")
            )
            chapters.append(chapter)

        if logger:
            logger.info(f"[获取章节列表] 成功获取章节列表, 书籍ID: {book_id}, 章节数: {len(chapters)}")
        return chapters
    except Exception as e:
        if logger:
            logger.error(f"[获取章节列表] 失败: {str(e)}, 书籍ID: {book_id}")
        return False


def get_book_detail(baseurl: str, book_id: int, logger=None, request_timeout: int = DEFAULT_TIMEOUT) -> Union[BookInfo, bool]:
    """
    获取书籍详细信息

    Args:
        baseurl: API基础URL，如 https://app.365ting.com/listen/Apitzg2025/
        book_id: 书籍ID
        uid: 用户ID (可选)
        logger: 日志记录器
        request_timeout: 请求超时时间（秒）

    Returns:
        BookInfo对象，失败返回False
    """
    try:
        url = f"{baseurl}book"
        params = {"bookId": book_id}

        if logger:
            logger.info(f"[获取书籍详情] 书籍ID: {book_id}, URL: {url}")

        headers = HEADERS.copy()
        response = requests.get(url, params=params, headers=headers, timeout=request_timeout)
        response.raise_for_status()
        data = response.json()

        if data.get("status") != 0:
            raise ValueError(f"API返回错误: {data.get('message', '未知错误')}, 书籍ID: {book_id}")

        book_data = data.get("data", {}).get("bookData", {})
        if not book_data or "id" not in book_data:
            raise ValueError(f"未找到书籍数据或ID缺失, 书籍ID: {book_id}")

        book_info = BookInfo(
            id=book_data.get("id", 0),
            count=int(book_data.get("count", 0)),
            UpdateStatus=book_data.get("bookUpdateStatus", 0),
            Image=book_data.get("bookImage", ""),
            Desc=book_data.get("bookDesc", ""),
            Title=book_data.get("bookTitle", ""),
            Anchor=book_data.get("bookAnchor", ""),
            Chapters=[]
        )

        if logger:
            logger.info(f"[获取书籍详情] 成功获取书籍信息: {book_info.Title}, 章节数: {book_info.count}")
        return book_info
    except Exception as e:
        if logger:
            logger.error(f"[获取书籍详情] 失败: {str(e)}, 书籍ID: {book_id}")
        return False


def get_base_url(logger=None, request_timeout: int = DEFAULT_TIMEOUT) -> Union[str, bool]:
    """
    获取基础URL配置

    Args:
        logger: 日志记录器
        request_timeout: 请求超时时间（秒）

    Returns:
        基础URL字符串（如 https://app.365ting.com/listen/Apitzg2025/），失败返回False
    """
    try:
        url = f"{CONFIG_URL}/config/tingchina2025.txt"
        headers = {
            "User-Agent": "okhttp/4.9.3",
            "Connection": "Keep-Alive",
            "Accept": "*/*",
            "Accept-Encoding": "gzip"
        }
        if logger:
            logger.info(f"[获取基础URL] 请求配置URL: {url}")
        response = requests.get(url, headers=headers, timeout=request_timeout)
        response.raise_for_status()
        return response.text.strip()
    except Exception as e:
        if logger:
            logger.error(f"[获取基础URL] 失败: {str(e)}")
        return False


def get_token(logger=None, request_timeout: int = DEFAULT_TIMEOUT) -> Union[str, bool]:
    """
    获取认证凭据Token

    Args:
        logger: 日志记录器
        request_timeout: 请求超时时间（秒）

    Returns:
        search_token字符串，失败返回False
    """
    try:
        url = f"{CONFIG_URL}/config/token.txt"
        headers = {
            "User-Agent": "okhttp/4.9.3",
            "Connection": "Keep-Alive",
            "Accept": "*/*",
            "Accept-Encoding": "gzip"
        }
        if logger:
            logger.info(f"[获取Token] 请求Token URL: {url}")
        response = requests.get(url, headers=headers, timeout=request_timeout)
        response.raise_for_status()
        text = response.text

        for line in text.splitlines():
            line = line.strip()
            if line.startswith("search_token="):
                token_value = line.split("=", 1)[1].strip()
                if logger:
                    logger.info(f"[获取Token] 成功获取search_token: {token_value}")
                return token_value

        raise ValueError(f"未找到search_token, 原始内容: {text}")
    except Exception as e:
        if logger:
            logger.error(f"[获取Token] 失败: {str(e)}")
        return False


def search_books(baseurl: str, keyword: str, search_token: str = "abcSEARCH-2025", client: str = "babala-android", logger=None, request_timeout: int = DEFAULT_TIMEOUT) -> Union[list[SearchResult], bool]:
    """
    搜索书籍

    Args:
        baseurl: API基础URL，如 https://app.365ting.com/listen/Apitzg2025/
        keyword: 搜索关键词
        search_token: 搜索Token
        client: 客户端类型
        logger: 日志记录器
        request_timeout: 请求超时时间（秒）

    Returns:
        SearchResult列表，失败返回False
    """
    try:
        url = f"{baseurl}appSearch"
        params = {
            "client": client,
            "search": keyword,
            "app_token": search_token
        }
        if logger:
            logger.info(f"[搜索书籍] 关键词: {keyword}, 客户端: {client}, URL: {url}")

        headers = HEADERS.copy()
        response = requests.get(url, params=params, headers=headers, timeout=request_timeout)
        response.raise_for_status()
        data = response.json()

        if data.get("status") != 0:
            raise ValueError(f"API返回错误: {data.get('message', '未知错误')}, 关键词: {keyword}")

        book_list = data.get("data", {}).get("bookData", [])
        if not book_list:
            raise ValueError(f"未找到搜索结果, 关键词: {keyword}")

        results = []
        for item in book_list:
            if "id" not in item:
                raise ValueError(f"搜索结果数据缺少id: {item}")

            result = SearchResult(
                id=item.get("id", 0),
                bookTitle=item.get("bookTitle", ""),
                bookDesc=item.get("bookDesc", ""),
                bookImage=item.get("bookImage", ""),
                bookAnchor=item.get("bookAnchor", ""),
                count=item.get("count", 0),
                UpdateStatus=item.get("bookUpdateStatus", 0),
                heat=item.get("heat", 0)
            )
            results.append(result)

        if logger:
            logger.info(f"[搜索书籍] 成功获取搜索结果, 关键词: {keyword}, 结果数: {len(results)}")
        return results
    except Exception as e:
        if logger:
            logger.error(f"[搜索书籍] 失败: {str(e)}, 关键词: {keyword}")
        return False


def get_chapter_url(baseurl: str, chapter_id: int, book_id: int, logger=None, request_timeout: int = DEFAULT_TIMEOUT, _is_retry: bool = False) -> Union[str, bool]:
    """
    获取章节音频URL

    Args:
        baseurl: API基础URL，如 https://app.365ting.com/listen/Apitzg2025/
        chapter_id: 章节ID
        book_id: 书籍ID
        logger: 日志记录器
        request_timeout: 请求超时时间（秒）
        _is_retry: 是否重试模式（重试模式直接使用新API）

    Returns:
        音频URL字符串，失败返回False
    """
    if not _is_retry:
        old_url = old_chapter_url_api.get_chapter_url(chapter_id, book_id, request_timeout, logger)
        if old_url:
            if logger:
                logger.info(f"[获取章节URL] 旧API成功, 章节ID: {chapter_id}, 书籍ID: {book_id}")
            return old_url
        if logger:
            logger.warning(f"[获取章节URL] 旧API失败，尝试新API, 章节ID: {chapter_id}, 书籍ID: {book_id}")
    
    try:
        timestamp = str(int(time.time() * 1000))
        add_it_parapet = get_add_it_parapet(timestamp)

        url = f"{baseurl}AppGetChapterUrl2023"
        params = {
            "timeStamp": timestamp,
            "chapterId": chapter_id,
            "addItParapet": add_it_parapet,
            "bookId": book_id
        }
        if logger:
            logger.info(f"[获取章节URL] 新API请求, 章节ID: {chapter_id}, 书籍ID: {book_id}, URL: {url}")

        headers = HEADERS.copy()
        response = requests.get(url, params=params, headers=headers, timeout=request_timeout)
        response.raise_for_status()
        data = response.json()

        if data.get("src"):
            if logger:
                logger.info(f"[获取章节URL] 新API成功, 章节ID: {chapter_id}")
            return data["src"]
        else:
            raise ValueError(f"不符合要求的结果：{data} 章节ID：{chapter_id} 书籍ID：{book_id}")
    except Exception as e:
        if logger:
            logger.error(f"[获取章节URL] 新API也失败: {str(e)}, 章节ID: {chapter_id}, 书籍ID: {book_id}")
        return False


if __name__ == "__main__":
    baseurl = "https://app.365ting.com/listen/Apitzg2025/"

    print("=== 测试获取目录 ===")
    chapters = get_chapter_list(baseurl, 29690)
    print(chapters)

    print("\n=== 测试获取书籍详细 ===")
    book = get_book_detail(baseurl, 29690)
    print(book)

    print("\n=== 测试获取baseurl ===")
    config_url = get_base_url()
    print(config_url)

    print("\n=== 测试获取token ===")
    token = get_token()
    print(token)

    print("\n=== 测试搜索 ===")
    results = search_books(baseurl, "深海余烬")
    print(results)

    print("\n=== 测试获取章节URL ===")
    chapter_url = get_chapter_url(baseurl, 17601468, 29690)
    print(chapter_url)
