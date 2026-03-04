import logging
import os
from logging.handlers import RotatingFileHandler

from src.config import LOG_DIR, SERVER_LOG_FILE, ACCESS_LOG_FILE

def setup_loggers():
    """Sets up the access and server loggers."""
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    server_log_path = SERVER_LOG_FILE
    access_log_path = ACCESS_LOG_FILE

    # Server Logger
    server_logger = logging.getLogger("server")
    server_logger.setLevel(logging.INFO)
    server_handler = RotatingFileHandler(server_log_path, maxBytes=10*1024*1024, backupCount=5)
    server_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    server_handler.setFormatter(server_formatter)
    if not server_logger.handlers:
        server_logger.addHandler(server_handler)
        server_logger.addHandler(logging.StreamHandler())

    # Access Logger
    access_logger = logging.getLogger("access")
    access_logger.setLevel(logging.INFO)
    access_handler = RotatingFileHandler(access_log_path, maxBytes=10*1024*1024, backupCount=5)
    access_formatter = logging.Formatter('%(asctime)s - %(message)s')
    access_handler.setFormatter(access_formatter)
    if not access_logger.handlers:
        access_logger.addHandler(access_handler)

    return server_logger, access_logger
