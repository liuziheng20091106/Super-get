"""
调试脚本 - 测试 Manager 模块所有功能
"""
import sys
sys.path.insert(0, '.')

from module.logger import get_logger
from module.manager import Manager

def main():
    logger_config = {
        'console': {'enabled': True, 'use_color': True, 'level': 'DEBUG'}
    }
    logger = get_logger('Test', logger_config)

    logger.info("=== 开始测试 Manager 模块 ===")

    # 1. 初始化 Manager
    logger.info("\n--- 测试1: 初始化 Manager ---")
    try:
        manager = Manager(logger=logger)
        logger.info(f"初始化成功, BaseURL: {manager.base_url}")
    except Exception as e:
        logger.error(f"初始化失败: {e}")
        return

    # 2. 搜索书籍
    logger.info("\n--- 测试2: 搜索书籍 '深海余烬' ---")
    results = manager.search_books("深海余烬")
    if results is False:
        logger.error("搜索失败")
        return
    logger.info(f"搜索到 {len(results)} 个结果")
    for i, r in enumerate(results[:3]):
        logger.info(f"  [{i}] {r.bookTitle} (ID: {r.id})")

    if not results:
        logger.error("未搜索到结果")
        return

    # 选择第一个结果
    search_result = results[0]
    logger.info(f"选择书籍: {search_result.bookTitle} (ID: {search_result.id})")

    # 3. 添加书籍
    logger.info("\n--- 测试3: 添加书籍到列表 ---")
    success = manager.add_book(search_result)
    logger.info(f"添加结果: {success}")

    if not success:
        logger.warning("书籍可能已存在，尝试获取已有书籍")
        book = manager.get_books()[0] if manager.get_books() else None
    else:
        book = manager.get_books()[0]

    if not book:
        logger.error("无法获取书籍对象")
        return

    logger.info(f"当前书籍: {book.Title} (ID: {book.id})")

    # 4. 获取书籍列表
    logger.info("\n--- 测试4: 获取书籍列表 ---")
    books = manager.get_books()
    logger.info(f"书籍列表长度: {len(books)}")

    # 5. 更新章节列表
    logger.info("\n--- 测试5: 更新章节列表 ---")
    chapters = manager.update_chapters(book)
    if chapters is False:
        logger.error("更新章节列表失败")
    else:
        logger.info(f"章节数: {len(chapters)}")
        if chapters:
            logger.info(f"  第一章: {chapters[0].title}")

    # 6. 获取未下载章节
    logger.info("\n--- 测试6: 获取未下载章节 ---")
    undownloaded = manager.get_undownloaded_chapters(book)
    logger.info(f"未下载章节数: {len(undownloaded)}")

    # 7. 设置章节下载状态
    logger.info("\n--- 测试7: 设置章节下载状态 ---")
    if chapters:
        chapter = chapters[0]
        logger.info(f"设置章节 '{chapter.title}' 为已下载")
        manager.set_chapter_downloaded(chapter, True)

        # 验证
        logger.info(f"下载状态: {chapter.downloaded}")

        # 再改回来
        manager.set_chapter_downloaded(chapter, False)
        logger.info(f"恢复为未下载: {chapter.downloaded}")

    # 8. 获取下载进度
    logger.info("\n--- 测试8: 获取下载进度 ---")
    progress = manager.get_download_progress(book)
    logger.info(f"进度: {progress}")

    # 9. 更新书籍详情
    logger.info("\n--- 测试9: 更新书籍详情 ---")
    updated_book = manager.update_book_detail(book)
    if updated_book:
        logger.info(f"更新后的标题: {updated_book.Title}")
    else:
        logger.error("更新书籍详情失败")

    # 10. 保存到 JSON
    logger.info("\n--- 测试10: 保存到 JSON ---")
    save_path = "data/test_books.json"
    save_success = manager.save_to_json(save_path)
    logger.info(f"保存结果: {save_success}")

    # 11. 从 JSON 加载
    logger.info("\n--- 测试11: 从 JSON 加载 ---")
    # 先清空当前列表
    manager.books.clear()
    logger.info(f"清空后书籍数: {len(manager.books)}")

    load_success = manager.load_from_json(save_path)
    logger.info(f"加载结果: {load_success}")
    logger.info(f"加载后书籍数: {len(manager.books)}")

    if manager.get_books():
        loaded_book = manager.get_books()[0]
        logger.info(f"加载的书籍: {loaded_book.Title}")
        logger.info(f"加载的章节数: {len(loaded_book.Chapters)}")

    # 12. 刷新所有章节
    logger.info("\n--- 测试12: 刷新所有书籍章节 ---")
    manager.refresh_all_chapters()
    logger.info("刷新完成")

    # 13. 移除书籍
    logger.info("\n--- 测试13: 移除书籍 ---")
    if manager.get_books():
        book_to_remove = manager.get_books()[0]
        remove_success = manager.remove_book(book_to_remove)
        logger.info(f"移除结果: {remove_success}")
        logger.info(f"移除后书籍数: {len(manager.books)}")

    logger.info("\n=== 测试完成 ===")

if __name__ == "__main__":
    main()
