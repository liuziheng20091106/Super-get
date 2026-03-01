"""
调试脚本 - 测试 Manager 集成 DownloadManager
"""
import sys
sys.path.insert(0, '.')

from module.logger import get_logger
from module.manager import Manager
from module.config import Config

def main():
    logger_config = {
        'console': {'enabled': True, 'use_color': True, 'level': 'DEBUG'}
    }
    logger = get_logger('Test', logger_config)
    config = Config()

    logger.info("=== 测试 Manager 集成 DownloadManager ===")

    # 1. 初始化 Manager（传入config）
    logger.info("\n--- 测试1: 初始化 Manager ---")
    manager = Manager(logger=logger, config=config)
    logger.info(f"初始化成功, BaseURL: {manager.base_url}")
    logger.info(f"Config: max_workers={config.max_workers}, request_interval={config.request_interval}")

    # 2. 搜索并添加书籍
    logger.info("\n--- 测试2: 搜索并添加书籍 ---")
    results = manager.search_books("深海余烬")
    if not results:
        logger.error("搜索失败")
        return

    manager.add_book(results[0])
    book = manager.get_books()[0]
    manager.update_chapters(book)
    logger.info(f"书籍: {book.Title}, 章节数: {len(book.Chapters)}")

    # 只取前10个章节测试
    test_chapters = book.Chapters[:10]
    logger.info(f"选择前 {len(test_chapters)} 个章节进行测试")

    # 3. 开始下载（使用集成的方法）
    logger.info("\n--- 测试3: 开始下载 ---")
    manager.start_download(book)

    # 等待一段时间让下载进行
    import time
    time.sleep(30)

    # 4. 查看下载状态
    logger.info("\n--- 测试4: 查看下载状态 ---")
    status = manager.get_download_status()
    logger.info(f"下载状态: {status}")

    # 5. 暂停
    logger.info("\n--- 测试5: 暂停下载 ---")
    manager.pause_download()
    time.sleep(2)
    status = manager.get_download_status()
    logger.info(f"暂停后状态: {status}")

    # 6. 恢复
    logger.info("\n--- 测试6: 恢复下载 ---")
    manager.resume_download()

    # 等待一会儿再取消
    time.sleep(2)

    # 7. 取消
    logger.info("\n--- 测试7: 取消下载 ---")
    manager.cancel_download()
    status = manager.get_download_status()
    logger.info(f"取消后状态: {status}")

    # 8. 检查章节下载状态
    logger.info("\n--- 测试8: 检查章节状态 ---")
    for ch in test_chapters:
        logger.info(f"  {ch.title}: downloaded={ch.downloaded}")

    logger.info("\n=== 测试完成 ===")

if __name__ == "__main__":
    main()
