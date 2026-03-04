import logging
import json
from src.utils.logger_factory import setup_loggers

server_logger, access_logger = setup_loggers()

def log_access(username: str, tool_name: str, params: dict):
    """Logs tool usage to access.log."""
    log_entry = {
        "username": username,
        "tool": tool_name,
        "parameters": params
    }
    access_logger.info(json.dumps(log_entry))

def log_server(level: str, message: str):
    """Logs messages to server.log."""
    if level.upper() == "INFO":
        server_logger.info(message)
    elif level.upper() == "ERROR":
        server_logger.error(message)
    elif level.upper() == "WARNING":
        server_logger.warning(message)
    else:
        server_logger.debug(message)
