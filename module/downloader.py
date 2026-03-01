"""
下载模块 - 负责下载章节音频文件
"""
import os
import time
import requests
from typing import Optional

from module.data_provider import ChapterInfo
from module.api_client import get_chapter_url


class Downloader:
    """
    下载器类，负责下载章节音频文件
    """

    def __init__(self, chapter_info: ChapterInfo, logger, config, base_url: str = ""):
        """
        初始化下载器

        :param chapter_info: 章节信息对象
        :param logger: 日志记录器
        :param config: 配置对象
        :param base_url: API基础URL
        """
        self.chapter_info = chapter_info
        self.logger = logger
        self.config = config
        self.baseurl = base_url

    def download(self) -> bool:
        """
        执行下载操作

        :return: 下载成功返回True，失败返回False
        """
        chapter_id = self.chapter_info.chapterid
        book_id = self.chapter_info.bookid
        chapter_title = self.chapter_info.title

        max_retries = self.config.get('max_retries', 3)
        download_timeout = self.config.get('download_timeout', 60)

        for attempt in range(1, max_retries + 1):
            try:
                if self.logger:
                    self.logger.info(f"[下载模块] 开始下载章节: {chapter_title}, 章节ID: {chapter_id}, 尝试 {attempt}/{max_retries}")

                audio_url = self._get_audio_url(chapter_id, book_id)
                if not audio_url:
                    if self.logger:
                        self.logger.warning(f"[下载模块] 获取音频URL失败, 章节ID: {chapter_id}")
                    continue

                save_path = self._get_save_path()
                if self._download_file(audio_url, save_path, download_timeout):
                    if self.logger:
                        self.logger.info(f"[下载模块] 下载成功: {chapter_title}, 保存路径: {save_path}")
                    return True
                else:
                    if self.logger:
                        self.logger.warning(f"[下载模块] 下载失败, 章节ID: {chapter_id}, 尝试 {attempt}/{max_retries}")

            except requests.exceptions.Timeout:
                if self.logger:
                    self.logger.warning(f"[下载模块] 下载超时, 章节ID: {chapter_id}, 尝试 {attempt}/{max_retries}")
            except requests.exceptions.ConnectionError as e:
                if self.logger:
                    self.logger.warning(f"[下载模块] 网络连接错误: {str(e)}, 章节ID: {chapter_id}, 尝试 {attempt}/{max_retries}")
            except requests.exceptions.RequestException as e:
                if self.logger:
                    self.logger.warning(f"[下载模块] 请求异常: {str(e)}, 章节ID: {chapter_id}, 尝试 {attempt}/{max_retries}")
            except IOError as e:
                if self.logger:
                    self.logger.warning(f"[下载模块] 文件IO错误: {str(e)}, 章节ID: {chapter_id}, 尝试 {attempt}/{max_retries}")
            except Exception as e:
                if self.logger:
                    self.logger.error(f"[下载模块] 未知错误: {str(e)}, 章节ID: {chapter_id}")
                return False

            if attempt < max_retries:
                wait_time = attempt * 2
                if self.logger:
                    self.logger.info(f"[下载模块] 等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)

        if self.logger:
            self.logger.error(f"[下载模块] 下载失败，已达到最大重试次数 {max_retries}, 章节ID: {chapter_id}")
        return False

    def _get_audio_url(self, chapter_id: int, book_id: int) -> Optional[str]:
        """
        获取音频下载链接

        :param chapter_id: 章节ID
        :param book_id: 书籍ID
        :return: 音频URL，失败返回None
        """
        try:
            result = get_chapter_url(self.baseurl, chapter_id, book_id, self.logger)
            if result and isinstance(result, str):
                return result
            return None
        except Exception as e:
            if self.logger:
                self.logger.error(f"[下载模块] 获取音频URL异常: {str(e)}")
            return None

    def _get_save_path(self) -> str:
        """
        获取文件保存路径

        :return: 保存路径
        """
        download_dir = self.config.get('default_download_dir', 'downloads')
        book_title = self.chapter_info.bookTitle or '未知书籍'
        safe_book_title = self._sanitize_filename(book_title)
        chapter_title = self.chapter_info.title or '未知章节'
        safe_chapter_title = self._sanitize_filename(chapter_title)
        position = self.chapter_info.position

        full_dir = os.path.join(download_dir, safe_book_title)
        os.makedirs(full_dir, exist_ok=True)

        filename = f"{position:04d}_{safe_chapter_title}.mp3"
        return os.path.join(full_dir, filename)

    def _sanitize_filename(self, filename: str) -> str:
        """
        清理文件名中的非法字符

        :param filename: 原始文件名
        :return: 清理后的文件名
        """
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename.strip()

    def _download_file(self, url: str, save_path: str, timeout: int) -> bool:
        """
        下载文件到本地

        :param url: 下载链接
        :param save_path: 保存路径
        :param timeout: 超时时间（秒）
        :return: 下载成功返回True，失败返回False
        """
        try:
            headers = {
                "User-Agent": "TingShiJie/1.8.8 (m.i275.com)",
                "Connection": "keep-alive",
                "Accept": "*/*",
                "Accept-Encoding": "gzip, deflate"
            }

            response = requests.get(url, headers=headers, timeout=timeout, stream=True)
            response.raise_for_status()

            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            return os.path.exists(save_path) and os.path.getsize(save_path) > 0

        except requests.exceptions.Timeout:
            if self.logger:
                self.logger.warning(f"[下载模块] 下载超时: URL={url}")
            if os.path.exists(save_path):
                try:
                    os.remove(save_path)
                except Exception:
                    pass
            return False
        except requests.exceptions.ConnectionError as e:
            if self.logger:
                self.logger.warning(f"[下载模块] 网络连接错误: {str(e)}")
            if os.path.exists(save_path):
                try:
                    os.remove(save_path)
                except Exception:
                    pass
            return False
        except requests.exceptions.HTTPError as e:
            if self.logger:
                self.logger.warning(f"[下载模块] HTTP错误: {str(e)}")
            if os.path.exists(save_path):
                try:
                    os.remove(save_path)
                except Exception:
                    pass
            return False
        except IOError as e:
            if self.logger:
                self.logger.warning(f"[下载模块] 文件IO错误: {str(e)}")
            return False
        except Exception as e:
            if self.logger:
                self.logger.error(f"[下载模块] 下载异常: {str(e)}")
            return False


def download_chapter(chapter_info: ChapterInfo, logger, config, base_url: str = "") -> bool:
    """
    下载章节音频文件

    :param chapter_info: 章节信息对象
    :param logger: 日志记录器
    :param config: 配置对象
    :param base_url: API基础URL
    :return: 下载成功返回True，失败返回False
    """
    downloader = Downloader(chapter_info, logger, config, base_url)
    return downloader.download()
