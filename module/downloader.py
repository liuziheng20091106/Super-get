"""
下载模块 - 负责下载章节音频文件
"""
import os
import time
import requests
from typing import Optional

from module.data_provider import ChapterInfo
from module.api_client import get_chapter_url

try:
    from mutagen.mp3 import MP3  # type: ignore
    from mutagen.id3 import ID3  # type: ignore
    from mutagen.id3._frames import TIT2, TPE1, TALB, TRCK, TDRC, APIC  # type: ignore
    from mutagen.mp4 import MP4, MP4Tags, MP4Cover  # type: ignore
    from mutagen.oggvorbis import OggVorbis  # type: ignore
    from mutagen.flac import FLAC  # type: ignore
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False
    MP3 = None
    MP4 = None
    MP4Tags = None
    MP4Cover = None
    OggVorbis = None
    FLAC = None
    TIT2 = None
    TPE1 = None
    TALB = None
    TRCK = None
    TDRC = None
    APIC = None


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
        request_timeout = self.config.get('request_timeout', 10)

        for attempt in range(1, max_retries + 1):
            try:
                if self.logger:
                    self.logger.info(f"[下载模块] 开始下载章节: {chapter_title}, 章节ID: {chapter_id}, 尝试 {attempt}/{max_retries}")

                audio_url = self._get_audio_url(chapter_id, book_id, request_timeout, _is_retry=(attempt > 1))
                if not audio_url:
                    if self.logger:
                        self.logger.warning(f"[下载模块] 获取音频URL失败, 章节ID: {chapter_id}")
                    continue

                file_ext = self._extract_extension(audio_url)
                save_path = self._get_save_path(file_ext)
                if self._download_file(audio_url, save_path, download_timeout, request_timeout):
                    self._write_metadata(save_path)
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
                wait_time = attempt * self.config.request_interval * 2
                if self.logger:
                    self.logger.info(f"[下载模块] 等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)

        if self.logger:
            self.logger.error(f"[下载模块] 下载失败，已达到最大重试次数 {max_retries}, 章节ID: {chapter_id}")
        return False

    def _get_audio_url(self, chapter_id: int, book_id: int, request_timeout: int, _is_retry: bool = False) -> Optional[str]:
        """
        获取音频下载链接

        :param chapter_id: 章节ID
        :param book_id: 书籍ID
        :param request_timeout: 请求超时时间（秒）
        :param _is_retry: 是否重试（内部使用）
        
        :return: 音频URL，失败返回None
        """
        try:
            result = get_chapter_url(self.baseurl, chapter_id, book_id, self.logger, request_timeout=request_timeout, _is_retry=_is_retry)
            if result and isinstance(result, str):
                return result
            return None
        except Exception as e:
            if self.logger:
                self.logger.error(f"[下载模块] 获取音频URL异常: {str(e)}")
            return None

    def _get_save_path(self, file_ext: str = '.mp3') -> str:
        """
        获取文件保存路径

        :param file_ext: 文件扩展名
        :return: 保存路径
        """
        download_dir = self.config.get('default_download_dir', 'downloads')
        book_title = self.chapter_info.bookTitle or '未知书籍'
        safe_book_title = self._sanitize_filename(book_title)
        book_anchor = self.chapter_info.bookAnchor or '未知主播'
        safe_book_anchor = self._sanitize_filename(book_anchor)
        chapter_title = self.chapter_info.title or '未知章节'
        safe_chapter_title = self._sanitize_filename(chapter_title)
        position = self.chapter_info.position

        full_dir = os.path.join(download_dir, f"{safe_book_title} - {safe_book_anchor}")
        os.makedirs(full_dir, exist_ok=True)

        filename = f"{position:04d}_{safe_chapter_title}{file_ext}"
        return os.path.join(full_dir, filename)

    def _extract_extension(self, url: str) -> str:
        """从URL中提取文件扩展名"""
        from urllib.parse import urlparse
        try:
            path = urlparse(url).path
            ext = os.path.splitext(path)[1].lower()
            if ext in ['.mp3', '.m4a', '.aac', '.ogg', '.flac', '.wav']:
                return ext
            if 'm4a' in url.lower():
                return '.m4a'
            if 'mp3' in url.lower():
                return '.mp3'
            if 'ogg' in url.lower():
                return '.ogg'
            if 'flac' in url.lower():
                return '.flac'
            if 'wav' in url.lower():
                return '.wav'
            if 'aac' in url.lower():
                return '.aac'
        except Exception:
            pass
        return '.mp3'

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

    def _write_metadata(self, file_path: str) -> bool:
        """
        写入音乐元数据

        :param file_path: 音乐文件路径
        :return: 是否成功写入
        """
        if not MUTAGEN_AVAILABLE:
            if self.logger:
                self.logger.info("[下载模块] mutagen 库未安装，无法写入元数据")
            return False

        try:
            level = self.config.music_metadata_level if hasattr(self.config, 'music_metadata_level') else 0
            self.logger.debug(f"[下载模块] 写入元数据, 级别: {level}")
            if level == 0:
                return True

            ext = os.path.splitext(file_path)[1].lower()
            
            if ext in ['.m4a', '.aac']:
                return self._write_m4a_metadata(file_path, level)
            elif ext == '.mp3':
                return self._write_mp3_metadata(file_path, level)
            elif ext == '.ogg':
                return self._write_ogg_metadata(file_path, level)
            elif ext == '.flac':
                return self._write_flac_metadata(file_path, level)
            elif ext == '.wav':
                return self._write_wav_metadata(file_path, level)
            else:
                if self.logger:
                    self.logger.info(f"[下载模块] 不支持的格式: {ext}")
                return True

        except Exception as e:
            if self.logger:
                self.logger.warning(f"[下载模块] 元数据写入失败: {str(e)}, 文件: {file_path}")
            return False

    def _write_mp3_metadata(self, file_path: str, level: int) -> bool:
        """写入 MP3 文件元数据"""
        audio = MP3(file_path)  # type: ignore

        if audio.tags is None:
            audio.add_tags()
        
        tags = audio.tags
        if tags is None:
            return False

        title = self.chapter_info.title or ''
        if title:
            tags['TIT2'] = TIT2(encoding=3, text=title)  # type: ignore

        album = self.chapter_info.bookTitle or ''
        if album:
            tags['TALB'] = TALB(encoding=3, text=album)  # type: ignore

        artist = self.chapter_info.bookAnchor or ''
        if artist:
            tags['TPE1'] = TPE1(encoding=3, text=artist)  # type: ignore

        position = self.chapter_info.position
        if position:
            tags['TRCK'] = TRCK(encoding=3, text=str(position))  # type: ignore

        tags['TDRC'] = TDRC(encoding=3, text=str(time.localtime().tm_year))  # type: ignore

        if level >= 2:
            self._add_cover_image(audio)

        audio.save()
        if self.logger:
            self.logger.info(f"[下载模块] MP3元数据写入成功: {file_path}, 级别: {level}")
        return True

    def _write_m4a_metadata(self, file_path: str, level: int) -> bool:
        """写入 M4A 文件元数据"""
        audio = MP4(file_path)  # type: ignore

        if audio.tags is None:
            audio.add_tags()
        
        tags = audio.tags
        if tags is None:
            return False

        title = self.chapter_info.title or ''
        if title:
            tags['\xa9nam'] = title

        album = self.chapter_info.bookTitle or ''
        if album:
            tags['\xa9alb'] = album

        artist = self.chapter_info.bookAnchor or ''
        if artist:
            tags['\xa9ART'] = artist

        position = self.chapter_info.position
        if position:
            tags['trkn'] = [(position, 0)]

        tags['\xa9day'] = str(time.localtime().tm_year)

        if level >= 2:
            self._add_m4a_cover(audio)

        audio.save()
        if self.logger:
            self.logger.info(f"[下载模块] M4A元数据写入成功: {file_path}, 级别: {level}")
        return True

    def _add_cover_image(self, audio) -> bool:
        """
        添加封面图片

        :param audio: MP3 对象
        :return: 是否成功添加
        """
        try:
            from module.api_client import get_book_detail
            book_id = self.chapter_info.bookid
            book_detail = get_book_detail(self.baseurl, book_id, logger=self.logger)
            if not book_detail or not getattr(book_detail, 'Image', None):
                return False

            headers = {
                "User-Agent": "TingShiJie/1.8.8 (m.i275.com)",
                "Connection": "keep-alive"
            }
            image_url = getattr(book_detail, 'Image', None)
            if not image_url:
                return False
            response = requests.get(image_url, headers=headers, timeout=10)
            if response.status_code == 200:
                if audio.tags is None:
                    audio.add_tags()
                tags = audio.tags
                if tags is None:
                    return False
                tags['APIC'] = APIC(  # type: ignore
                    encoding=3,
                    mime=response.headers.get('Content-Type', 'image/jpeg'),
                    type=3,
                    desc='Cover',
                    data=response.content
                )
                return True
        except Exception as e:
            if self.logger:
                self.logger.warning(f"[下载模块] 添加封面失败: {str(e)}")
        return False

    def _add_m4a_cover(self, audio) -> bool:
        """添加 M4A 封面图片"""
        try:
            from module.api_client import get_book_detail
            book_id = self.chapter_info.bookid
            book_detail = get_book_detail(self.baseurl, book_id, logger=self.logger)
            if not book_detail or not getattr(book_detail, 'Image', None):
                return False

            headers = {
                "User-Agent": "TingShiJie/1.8.8 (m.i275.com)",
                "Connection": "keep-alive"
            }
            image_url = getattr(book_detail, 'Image', None)
            if not image_url:
                return False
            response = requests.get(image_url, headers=headers, timeout=10)
            if response.status_code == 200:
                if audio.tags is None:
                    audio.add_tags()
                tags = audio.tags
                if tags is None:
                    return False
                tags['covr'] = [MP4Cover(response.content, imageformat=MP4Cover.FORMAT_JPEG)]  # type: ignore
                return True
        except Exception as e:
            if self.logger:
                self.logger.warning(f"[下载模块] 添加M4A封面失败: {str(e)}")
        return False

    def _write_ogg_metadata(self, file_path: str, level: int) -> bool:
        """写入 OGG 文件元数据"""
        audio = OggVorbis(file_path)  # type: ignore

        if audio.tags is None:
            audio.add_tags()
        
        tags = audio.tags
        if tags is None:
            return False

        title = self.chapter_info.title or ''
        if title:
            tags['TITLE'] = [title]  # type: ignore

        album = self.chapter_info.bookTitle or ''
        if album:
            tags['ALBUM'] = [album]  # type: ignore

        artist = self.chapter_info.bookAnchor or ''
        if artist:
            tags['ARTIST'] = [artist]  # type: ignore

        position = self.chapter_info.position
        if position:
            tags['TRACKNUMBER'] = [str(position)]  # type: ignore

        tags['DATE'] = [str(time.localtime().tm_year)]  # type: ignore

        if level >= 2:
            self._add_ogg_flac_cover(audio)

        audio.save()
        if self.logger:
            self.logger.info(f"[下载模块] OGG元数据写入成功: {file_path}, 级别: {level}")
        return True

    def _write_flac_metadata(self, file_path: str, level: int) -> bool:
        """写入 FLAC 文件元etadata"""
        audio = FLAC(file_path)  # type: ignore

        if audio.tags is None:
            audio.add_tags()
        
        tags = audio.tags
        if tags is None:
            return False

        title = self.chapter_info.title or ''
        if title:
            tags['TITLE'] = [title]  # type: ignore

        album = self.chapter_info.bookTitle or ''
        if album:
            tags['ALBUM'] = [album]  # type: ignore

        artist = self.chapter_info.bookAnchor or ''
        if artist:
            tags['ARTIST'] = [artist]  # type: ignore

        position = self.chapter_info.position
        if position:
            tags['TRACKNUMBER'] = [str(position)]  # type: ignore

        tags['DATE'] = [str(time.localtime().tm_year)]  # type: ignore

        if level >= 2:
            self._add_ogg_flac_cover(audio)

        audio.save()
        if self.logger:
            self.logger.info(f"[下载模块] FLAC元数据写入成功: {file_path}, 级别: {level}")
        return True

    def _write_wav_metadata(self, file_path: str, level: int) -> bool:
        """写入 WAV 文件元数据"""
        try:
            import wave
            with wave.open(file_path, 'r') as wav:
                if wav.getnframes() > 0:
                    if self.logger:
                        self.logger.info(f"[下载模块] WAV文件不支持ID3元数据，跳过: {file_path}")
            return True
        except Exception as e:
            if self.logger:
                self.logger.warning(f"[下载模块] WAV元数据写入失败: {str(e)}, 文件: {file_path}")
            return False

    def _add_ogg_flac_cover(self, audio) -> bool:
        """添加 OGG/FLAC 封面图片"""
        try:
            from module.api_client import get_book_detail
            book_id = self.chapter_info.bookid
            book_detail = get_book_detail(self.baseurl, book_id, logger=self.logger)
            if not book_detail or not getattr(book_detail, 'Image', None):
                return False

            headers = {
                "User-Agent": "TingShiJie/1.8.8 (m.i275.com)",
                "Connection": "keep-alive"
            }
            image_url = getattr(book_detail, 'Image', None)
            if not image_url:
                return False
            response = requests.get(image_url, headers=headers, timeout=10)
            if response.status_code == 200:
                if audio.tags is None:
                    audio.add_tags()
                tags = audio.tags
                if tags is None:
                    return False
                tags['METADATA_BLOCK_PICTURE'] = [self._create_flac_picture(response.content)]  # type: ignore
                return True
        except Exception as e:
            if self.logger:
                self.logger.warning(f"[下载模块] 添加OGG/FLAC封面失败: {str(e)}")
        return False

    def _create_flac_picture(self, image_data: bytes) -> str:
        """创建 FLAC 图片元数据块"""
        import struct
        import base64
        
        mime_type = 'image/jpeg'
        description = b''
        width = 0
        height = 0
        depth = 24
        
        picture_type = 3
        
        data = struct.pack('>I', picture_type)
        data += struct.pack('>I', len(mime_type))
        data += mime_type.encode('utf-8')
        data += struct.pack('>I', len(description))
        data += description
        data += struct.pack('>I', width)
        data += struct.pack('>I', height)
        data += struct.pack('>I', depth)
        data += struct.pack('>I', len(image_data))
        data += image_data
        
        return base64.b64encode(data).decode('ascii')

    def _download_file(self, url: str, save_path: str, timeout: int, request_timeout: int) -> bool:
        """
        下载文件到本地

        :param url: 下载链接
        :param save_path: 保存路径
        :param timeout: 超时时间（秒）
        :param request_timeout: 请求超时时间（秒）
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
