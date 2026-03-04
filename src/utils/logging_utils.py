import logging
import json
from src.utils.logger_factory import setup_loggers

server_logger, access_logger = setup_loggers()

USAGE_LOG_FILE = os.path.join(LOG_DIR, "usage.log")

def log_access(username: str, tool_name: str, params: dict):
    """Logs tool usage to access.log."""
    log_entry = {
        "username": username,
        "tool": tool_name,
        "parameters": params
    }
    access_logger.info(json.dumps(log_entry))

def log_usage(kind: str, name: str, params: dict):
    """
    Writes tool/resource usage to logs/usage.log
    Format: <ISO_TIMESTAMP> | <kind>=<name> | params=<dict>
    """
    timestamp = datetime.utcnow().isoformat()
    # Ensure log dir exists (though main.py usually does this)
    os.makedirs(os.path.dirname(USAGE_LOG_FILE), exist_ok=True)
    with open(USAGE_LOG_FILE, "a") as f:
        f.write(f"{timestamp} | {kind}={name} | params={params}\n")

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
