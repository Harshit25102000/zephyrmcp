"""
Configuration for Zephyr MCP Server.
Users should modify these values or use environment variables where applicable.
"""

import os

# Jira / Zephyr Configuration
JIRA_BASE_URL = os.getenv("JIRA_BASE_URL", "http://stg-jira.nomura.com")
JIRA_TIMEOUT = int(os.getenv("JIRA_TIMEOUT", "30"))

# MCP Server Configuration
MCP_NAME = "zephyr-mcp"
MCP_VERSION = "1.0.0"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
PORT = int(os.getenv("PORT", "9002"))

# Rate Limiting Configuration
# Prevents misuse like fetching too many projects or creating too many tests at once.
MAX_PROJECTS_PER_QUERY = int(os.getenv("MAX_PROJECTS_PER_QUERY", "2"))
MAX_TESTS_PER_BULK = int(os.getenv("MAX_TESTS_PER_BULK", "5"))

# Window-based Rate Limiting Configuration
# Define how many requests are allowed in a specific timeframe (window) in seconds.
RATE_LIMIT_COUNT = int(os.getenv("RATE_LIMIT_COUNT", "5"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "10"))

# Directory for logs
LOG_DIR = "logs"
SERVER_LOG_FILE = os.path.join(LOG_DIR, "server.log")
ACCESS_LOG_FILE = os.path.join(LOG_DIR, "access.log")
