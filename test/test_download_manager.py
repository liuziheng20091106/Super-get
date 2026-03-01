"""
调试脚本 - 测试 DownloadManager 下载功能
"""
import sys
sys.path.insert(0, '.')

from module.logger import get_logger
from module.manager import Manager
from module.download_manager import DownloadManager, TaskStatus

def main():
    logger_config = {
        'console': {'enabled': True, 'use_color': True, 'level': 'DEBUG'}
    }
    logger = get_logger('Test', logger_config)

    config = {
        'max_workers': 4,
        'request_interval': 0.5,
        'max_retries': 3,
        'download_timeout': 60,
        'default_download_dir': 'downloads'
    }

    logger.info("=== 开始测试 DownloadManager ===")

    # 1. 初始化 Manager
    logger.info("\n--- 测试1: 初始化 Manager ---")
    manager = Manager(logger=logger)
    logger.info(f"初始化成功")

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

    # 只取前3个章节测试
    test_chapters = book.Chapters[:3]
    logger.info(f"选择前 {len(test_chapters)} 个章节进行测试")

    # 3. 创建下载管理器
    logger.info("\n--- 测试3: 创建下载管理器 ---")
    completed_chapters = []
    
    def on_complete(chapter, success):
        completed_chapters.append((chapter, success))
        logger.info(f"回调: {chapter.title}, 成功: {success}")
        # 实时更新 Manager 状态
        manager.set_chapter_downloaded(chapter, success)
    
    download_manager = DownloadManager(
        config=config,
        logger=logger,
        base_url=manager.base_url,
        on_complete=on_complete
    )
    logger.info(f"下载管理器创建成功")

    # 4. 添加任务
    logger.info("\n--- 测试4: 添加下载任务 ---")
    download_manager.add_tasks(test_chapters)
    logger.info(f"已添加 {len(test_chapters)} 个任务")

    # 5. 查看状态
    logger.info("\n--- 测试5: 查看任务状态 ---")
    status = download_manager.get_status()
    logger.info(f"初始状态: {status}")

    # 6. 启动下载
    logger.info("\n--- 测试6: 启动下载 ---")
    download_manager.start()

    # 等待一会儿查看状态
    import time
    time.sleep(2)
    status = download_manager.get_status()
    logger.info(f"运行中状态: {status}")

    # 7. 暂停测试
    logger.info("\n--- 测试7: 暂停下载 ---")
    download_manager.pause()
    time.sleep(1)
    status = download_manager.get_status()
    logger.info(f"暂停状态: {status}")

    # 8. 恢复下载
    logger.info("\n--- 测试8: 恢复下载 ---")
    download_manager.resume()

    # 等待完成
    logger.info("\n--- 等待下载完成 ---")
    download_manager.wait()
    status = download_manager.get_status()
    logger.info(f"最终状态: {status}")

    # 9. 验证回调和状态更新
    logger.info("\n--- 测试9: 验证回调和状态更新 ---")
    logger.info(f"完成回调次数: {len(completed_chapters)}")
    for chapter, success in completed_chapters:
        logger.info(f"  - {chapter.title}: {'成功' if success else '失败'}")

    # 检查 Manager 中的状态
    logger.info("\n--- 测试10: 检查 Manager 状态 ---")
    for ch in test_chapters:
        logger.info(f"  {ch.title}: downloaded={ch.downloaded}")

    # 10. 取消功能测试
    logger.info("\n--- 测试11: 测试取消功能 ---")
    download_manager.add_tasks(test_chapters[:1])
    download_manager.start()
    time.sleep(0.5)
    download_manager.cancel()
    status = download_manager.get_status()
    logger.info(f"取消后状态: {status}")

    logger.info("\n=== 测试完成 ===")

if __name__ == "__main__":
    main()
