---
alwaysApply: true
---
# 日志记录规范

1. 所有日志记录必须使用 `logger` 对象，禁止使用 `print()` 或其他方式。
2. `logger` 参数从 `main()` 开始向下传递，签名示例：`def func(arg1, logger=None):`
3. 若未传入 `logger`，则默认为 `None`，使用时需判断：`if logger: logger.info("消息")`
4. 日志内容必须使用中文记录。
5. 日志格式：`[模块名] 操作描述 + 上下文信息`
