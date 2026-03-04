"""
Configuration for Zephyr MCP Server.
Users should modify these values or use environment variables where applicable.
"""

import os

# Automatically resolve the root project directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Jira / Zephyr Configuration
JIRA_BASE_URL = os.getenv("JIRA_BASE_URL", "http://stg-jira.nomura.com").rstrip("/")
JIRA_TIMEOUT = int(os.getenv("JIRA_TIMEOUT", "30"))
JIRA_VERIFY_SSL = os.getenv("JIRA_VERIFY_SSL", "False").lower() == "true"

# Derived API URLs
ZAPI_BASE_URL = f"{JIRA_BASE_URL}/rest/zapi/latest"
JIRA_API_URL = f"{JIRA_BASE_URL}/rest/api/2"

# MCP Server Configuration
MCP_NAME = "zephyr-mcp"
MCP_VERSION = "1.0.0"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
PORT = int(os.getenv("PORT", "5000"))

# Rate Limiting Configuration
# Prevents misuse like fetching too many projects or creating too many tests at once.
# Window-based Rate Limiting Configuration
# Define how many requests are allowed in a specific timeframe (window) in seconds.
RATE_LIMIT_COUNT = int(os.getenv("RATE_LIMIT_COUNT", "5"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "10"))

# Directory for logs (absolute path)
LOG_DIR = os.path.abspath(os.path.join(BASE_DIR, "logs"))
SERVER_LOG_FILE = os.path.join(LOG_DIR, "server.log")
ACCESS_LOG_FILE = os.path.join(LOG_DIR, "access.log")
USAGE_LOG_FILE = os.path.join(LOG_DIR, "usage.log")
