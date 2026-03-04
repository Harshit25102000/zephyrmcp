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

# Tool Usage Limits
# TOOL_MAX_ITEMS: Maximum number of items allowed in a single bulk tool call.
#   Examples: issue_ids in add_test_cases_to_cycle, execution_ids in bulk_execute_tests,
#             number of cycles a user can request at once via get_cycles.
#   If a user asks to create/fetch/execute more than this number in one call, the server
#   will reject the request with an actionable error message.
TOOL_MAX_ITEMS = int(os.getenv("TOOL_MAX_ITEMS", "5"))

# BULK_MAX_ITEMS: Separate, higher limit for explicitly bulk tools
#   (e.g. add_test_cases_to_cycle, bulk_execute_tests).
#   These tools are designed to batch many items, so they get a higher ceiling
#   than general list/query tools controlled by TOOL_MAX_ITEMS.
BULK_MAX_ITEMS = int(os.getenv("BULK_MAX_ITEMS", "10")) 

# MAX_RESULTS: Maximum number of records fetched from Zephyr/Jira list endpoints per request.
#   This caps the list size returned to the LLM to avoid oversized responses.
MAX_RESULTS = int(os.getenv("MAX_RESULTS", "50"))

# Directory for logs (absolute path)
LOG_DIR = os.path.abspath(os.path.join(BASE_DIR, "logs"))
SERVER_LOG_FILE = os.path.join(LOG_DIR, "server.log")
ACCESS_LOG_FILE = os.path.join(LOG_DIR, "access.log")
USAGE_LOG_FILE = os.path.join(LOG_DIR, "usage.log")
