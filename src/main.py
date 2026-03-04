import os
import logging
from src.config import PORT, LOG_DIR, SERVER_LOG_FILE

# ============================================================
# LOG DIRECTORY SETUP
# ============================================================
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(SERVER_LOG_FILE),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger("zephyr-mcp")

# ============================================================
# MCP SERVER INITIALIZATION
# ============================================================
from fastmcp import FastMCP
from src.tools.tests import register_test_tools
from src.tools.cycles import register_cycle_tools
from src.tools.executions import register_execution_tools

mcp = FastMCP("Zephyr MCP")

# Modular registrations
register_test_tools(mcp)
register_cycle_tools(mcp)
register_execution_tools(mcp)

# ============================================================
# HEALTH & INFO
# ============================================================

@mcp.tool()
async def health_check() -> dict:
    """Check if the Zephyr MCP server is running."""
    return {"status": "ok", "service": "zephyr-mcp"}

@mcp.resource("zephyr://system/info")
async def system_info() -> str:
    """Returns basic system information for the Zephyr MCP server."""
    return "Zephyr MCP Server v1.0.0\nStatus: Operational"

# ============================================================
# SERVER START
# ============================================================

if __name__ == "__main__":
    logger.info(f"Starting Zephyr MCP server on port {PORT}")
    logger.info(f"Logs directory: {LOG_DIR}")
    mcp.run(transport="http", port=PORT)
