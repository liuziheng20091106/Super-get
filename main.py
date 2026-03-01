from logger import get_logger
from config import get_config


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
    logger.info(f"程序启动")
if __name__ == "__main__":
    main()