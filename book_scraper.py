import requests
import urllib3
from config import Config
from logger import get_logger

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = get_logger(__name__)


def download_book_page(book_id: int) -> str:
    url = f"https://i275.com/book/{book_id}.html"
    logger.info(f"正在下载书籍页面: {url}")

    try:
        response = requests.get(
            url,
            headers=Config.get_headers(),
            timeout=Config().REQUEST_TIMEOUT,
            verify=False
        )
        response.raise_for_status()
        logger.info(f"成功下载书籍页面，页面大小: {len(response.text)} 字符")
        return response.text

    except requests.exceptions.RequestException as e:
        logger.error(f"下载书籍页面失败: {e}")
        return ""