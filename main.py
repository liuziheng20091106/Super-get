from module.logger import get_logger
from module.config import get_config
from module.manager import Manager
from api import create_app
import uvicorn

def main():
    config = get_config("config.json")
    logger_config = {
        'console': {'enabled': True, 'use_color': True, 'level': config.log_level}
    }
    logger = get_logger('365Ting', logger_config)
    logger.add_timed_file_handler(
        filename='logs/app.log',
        when='H',
        interval=1,
        backup_count=24,
        level=config.log_level
    )
    logger.info(f"程序启动，版本：{config.version}")
    manager = Manager(logger=logger)
    app = create_app(manager)
    uvicorn.run(app, host="0.0.0.0", port=5000)
    logger.info(f"程序退出")
if __name__ == "__main__":
    main()