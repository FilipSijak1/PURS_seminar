import logging
from logging.handlers import TimedRotatingFileHandler
import os
from datetime import datetime
import coloredlogs

def setup_logging():
    # Ensure the logs directory exists
    logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    # Set up logging for app
    app_log_file_path = os.path.join(logs_dir, f'app_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    app_handler = TimedRotatingFileHandler(app_log_file_path, when="midnight", interval=1, backupCount=7, encoding='utf-8')
    app_handler.setLevel(logging.INFO)
    app_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    app_handler.setFormatter(app_formatter)
    app_logger = logging.getLogger('app')
    app_logger.addHandler(app_handler)
    app_logger.setLevel(logging.INFO)  # Ensure the logger level is set

    # Set up logging for script.js
    script_log_file_path = os.path.join(logs_dir, f'script_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    script_handler = TimedRotatingFileHandler(script_log_file_path, when="midnight", interval=1, backupCount=7, encoding='utf-8')
    script_handler.setLevel(logging.INFO)
    script_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    script_handler.setFormatter(script_formatter)
    script_logger = logging.getLogger('scriptLogger')
    script_logger.addHandler(script_handler)
    script_logger.setLevel(logging.INFO)

    # Set up coloredlogs
    coloredlogs.install(level='INFO', logger=app_logger, fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    coloredlogs.install(level='INFO', logger=script_logger, fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    return app_logger, script_logger