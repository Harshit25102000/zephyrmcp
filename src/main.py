from mcp.server.fastmcp import FastMCP
from typing import Any
from src.middleware.rate_limit import RateLimiter
from src.utils.logging_utils import log_server
from src.tools.tests import register_test_tools
from src.tools.cycles import register_cycle_tools
from src.tools.executions import register_execution_tools
from src.config import PORT, RATE_LIMIT_COUNT, RATE_LIMIT_WINDOW_SECONDS

# Detailed server instruction for the LLM
SERVER_INSTRUCTION = f"""
This MCP server provides a comprehensive interface for Zephyr (Jira Data Center plugin).
It is designed to handle the full QA lifecycle, from test creation and step management 
to cycle planning and final execution validation with attachments.

IMPORTANT:
1. This server implements a window-based rate limiter (Sliding Window).
   - Rate Limit: {RATE_LIMIT_COUNT} requests per every {RATE_LIMIT_WINDOW_SECONDS} seconds.
   - If you receive a 'Rate limit exceeded' error, please wait before retrying.
2. Authentication: The server expects Jira credentials (token or basic auth) in the request headers.
3. Errors: Error responses include specific ZAPI/Jira details when available. 
   401/403 errors usually indicate expired or insufficient permission for the provided token.
"""

# Initialize FastMCP server with rich instructions
mcp = FastMCP(
    "Zephyr MCP", 
    instructions=SERVER_INSTRUCTION
)

# Initialize Rate Limiter
limiter = RateLimiter()

# Register modular tools
register_test_tools(mcp, limiter)
register_cycle_tools(mcp, limiter)
register_execution_tools(mcp, limiter)

if __name__ == "__main__":
    log_server("INFO", f"Starting Zephyr MCP server on port {PORT}")
    # Support HTTP transport for streamable mode
    mcp.run(transport="http", port=PORT)
