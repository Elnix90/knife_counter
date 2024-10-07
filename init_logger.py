import os
import logging
from logging.handlers import RotatingFileHandler
import sys

def setup_logger(file_name):
    # Ensure the logging directory exists
    log_dir = 'logging'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Configure the logger
    logger = logging.getLogger(file_name)
    
    # Only add handlers if the logger doesn't already have handlers
    if not logger.handlers:
        log_file = os.path.join(log_dir, f'{file_name}.log')
        max_log_size = 5 * 1024 * 1024  # 5 MB
        backup_count = 3

        # File handler with UTF-8 encoding
        file_handler = RotatingFileHandler(log_file, maxBytes=max_log_size, backupCount=backup_count, encoding='utf-8')
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)

        logger.setLevel(logging.INFO)
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger
