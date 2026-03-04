import os
import httpx
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from fastmcp import FastMCP
from fastmcp.server.context import Context

# ============================================================
# CONFIG
# ============================================================

from src.config import (
    JIRA_BASE_URL, JIRA_API_URL, ZAPI_BASE_URL,
    JIRA_TIMEOUT, JIRA_VERIFY_SSL,
    PORT, LOG_DIR, SERVER_LOG_FILE, USAGE_LOG_FILE,
    RATE_LIMIT_COUNT, RATE_LIMIT_WINDOW_SECONDS,
)
from src.middleware.rate_limit import RateLimiter

# ============================================================
# LOGGING
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
# MCP SERVER — with full LLM-facing instruction
# ============================================================

SERVER_INSTRUCTION = f"""
You are connected to the Zephyr MCP Server — a comprehensive interface for Zephyr Scale (Jira Data Center plugin).

## Purpose
This server provides tools and resources for the full QA lifecycle:
- Test case creation and step management
- Test cycle planning (create, clone, edit, delete)
- Test execution recording and result tracking
- Attachment management for execution evidence

## Authentication — REQUIRED
Every tool call requires credentials. Send one of:
1. Bearer Token:   Authorization: Bearer <your_token>
2. Basic Auth:     username: <user>   AND   password: <pass>  (as separate headers)
If credentials are missing, you will get a "Credentials not provided" error. Do NOT retry without fixing the headers.

## Rate Limiting — STRICT
This server enforces a sliding-window rate limit:
- Limit: {RATE_LIMIT_COUNT} requests per {RATE_LIMIT_WINDOW_SECONDS} seconds per user/token
- If you receive "Rate limit exceeded", STOP immediately and wait {RATE_LIMIT_WINDOW_SECONDS} seconds before retrying.
- Do NOT retry in a tight loop. Batch your work into fewer, larger tool calls where possible.
- Bulk tools (e.g. add_test_cases_to_cycle, bulk_execute_tests) exist precisely to reduce API calls.

## Error Handling
All errors include detailed messages. Common patterns:
- HTTP 401/403: Expired or insufficient credentials. Re-authenticate.
- HTTP 404: The resource (test, cycle, execution) does not exist. Verify the ID.
- HTTP 429: Rate limit hit — wait before retrying.
- "Credentials not provided": Add the required authentication header.
- "Rate limit exceeded": Wait {RATE_LIMIT_WINDOW_SECONDS}s before calling again.
- "No HTTP request context": Server misconfiguration — use HTTP transport only.

## Resources vs Tools
- Resources (zephyr://...): Read-only data fetching. Use these for discovery and listing.
- Tools: Write operations (create, update, delete, execute). Use only when you need to change state.

## Key Numeric IDs
- project_id: Numeric Jira project ID (find with get_projects tool)
- version_id: Numeric Jira version ID (use -1 for unscheduled)
- cycle_id: Numeric Zephyr cycle ID (find with get_cycles tool)
- execution_id: Numeric execution ID (find with get_executions_by_cycle tool)
- issue_id: Numeric Jira issue ID (different from issue_key like 'QA-123')
"""

mcp = FastMCP("zephyr-mcp", instructions=SERVER_INSTRUCTION)
limiter = RateLimiter(limit=RATE_LIMIT_COUNT, window=RATE_LIMIT_WINDOW_SECONDS)

# ============================================================
# USAGE LOGGING
# ============================================================

def log_usage(kind: str, name: str, params: dict):
    """Write tool/resource usage to logs/usage.log."""
    timestamp = datetime.utcnow().isoformat()
    with open(USAGE_LOG_FILE, "a") as f:
        f.write(f"{timestamp} | {kind}={name} | params={params}\n")

# ============================================================
# AUTH EXTRACTION
# ============================================================

def extract_zephyr_auth(ctx: Context) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Extract auth credentials from the HTTP request context.
    Supports Bearer token (Authorization header) or Basic Auth (username/password headers).
    Returns: (username, password, token) — one of token or (username, password) will be set.
    Raises RuntimeError with actionable message if credentials are missing.
    """
    request = getattr(ctx, "request", None)
    if not request and hasattr(ctx, "request_context"):
        request = ctx.request_context.request

    if not request:
        raise RuntimeError(
            "No HTTP request context found. This server requires HTTP transport. "
            "Ensure you are connecting via streamable HTTP, not stdio."
        )

    headers = request.headers

    auth_header = headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        return None, None, token

    username = headers.get("username") or headers.get("Username")
    password = headers.get("password") or headers.get("Password")

    if username and password:
        return username, password, None

    raise RuntimeError(
        "Credentials not provided. "
        "Send 'Authorization: Bearer <token>' "
        "OR 'username' and 'password' as separate HTTP headers. "
        "Do not retry this call without adding the required credential headers."
    )

# ============================================================
# RATE LIMITING
# ============================================================

def check_rate_limit(ctx: Context):
    """
    Enforce per-user sliding window rate limiting.
    Raises RuntimeError if the limit is exceeded.
    """
    request = getattr(ctx, "request", None)
    if not request and hasattr(ctx, "request_context"):
        request = ctx.request_context.request

    headers = request.headers if request else {}
    auth_header = headers.get("authorization", "")
    username = headers.get("username", "anonymous")

    if "bearer" in auth_header.lower():
        identifier = auth_header.split(" ", 1)[-1].strip()[:20]  # truncate for logging
    else:
        identifier = username

    if not limiter.is_allowed(identifier):
        raise RuntimeError(
            f"Rate limit exceeded: max {RATE_LIMIT_COUNT} requests per {RATE_LIMIT_WINDOW_SECONDS} seconds. "
            f"Please wait {RATE_LIMIT_WINDOW_SECONDS} seconds before retrying. "
            "Use bulk tools (add_test_cases_to_cycle, bulk_execute_tests) to reduce API calls."
        )

# ============================================================
# HTTP REQUEST UTILITY
# ============================================================

async def zephyr_request(
    method: str,
    url: str,
    username: Optional[str] = None,
    password: Optional[str] = None,
    token: Optional[str] = None,
    params: Optional[dict] = None,
    json_data: Optional[dict] = None,
) -> Any:
    """
    Async HTTP requester for Zephyr/Jira APIs.
    Handles auth, SSL, timeouts, and error formatting.
    """
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    auth = None

    if token:
        headers["Authorization"] = f"Bearer {token}"
    elif username and password:
        auth = (username, password)

    async with httpx.AsyncClient(timeout=JIRA_TIMEOUT, verify=JIRA_VERIFY_SSL) as client:
        response = await client.request(method, url, headers=headers, auth=auth, params=params, json=json_data)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            try:
                detail = e.response.json()
            except Exception:
                detail = e.response.text
            status = e.response.status_code
            hint = {
                401: "Authentication failed. Check your credentials.",
                403: "Access denied. Your token may lack required permissions.",
                404: "Resource not found. Verify the ID/key you provided.",
                429: f"Zephyr API rate limit hit. Wait before retrying.",
                500: "Jira/Zephyr server error. Try again later.",
            }.get(status, "Unexpected error from Jira/Zephyr API.")
            raise RuntimeError(f"HTTP {status}: {hint} Detail: {detail}")
        try:
            return response.json()
        except Exception:
            return response.text


async def zephyr_upload(
    url: str,
    files: dict,
    username: Optional[str] = None,
    password: Optional[str] = None,
    token: Optional[str] = None,
) -> Any:
    """Multipart upload for attachments. SSL and timeout from config."""
    headers = {"Accept": "application/json"}
    auth = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    elif username and password:
        auth = (username, password)

    async with httpx.AsyncClient(timeout=JIRA_TIMEOUT, verify=JIRA_VERIFY_SSL) as client:
        response = await client.post(url, headers=headers, auth=auth, files=files)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Upload failed HTTP {e.response.status_code}: {e.response.text}")
        return response.json()

# ============================================================
# TOOL REGISTRATION
# ============================================================

from src.tools.tests import register_test_tools
from src.tools.cycles import register_cycle_tools
from src.tools.executions import register_execution_tools

register_test_tools(mcp, JIRA_API_URL, ZAPI_BASE_URL, log_usage, extract_zephyr_auth, check_rate_limit, zephyr_request, zephyr_upload)
register_cycle_tools(mcp, JIRA_API_URL, ZAPI_BASE_URL, log_usage, extract_zephyr_auth, check_rate_limit, zephyr_request)
register_execution_tools(mcp, JIRA_API_URL, ZAPI_BASE_URL, log_usage, extract_zephyr_auth, check_rate_limit, zephyr_request, zephyr_upload)

# ============================================================
# HEALTH CHECK
# ============================================================

@mcp.tool()
async def health_check() -> dict:
    """
    Check if the Zephyr MCP server is running and return its configuration summary.

    Use this tool first to verify connectivity and understand server limits before
    executing other operations.

    Output:
    {
      status: "ok",
      service: "zephyr-mcp",
      jira_base_url: string,
      rate_limit: string,
      ssl_verify: boolean
    }
    """
    log_usage("tool", "health_check", {})
    return {
        "status": "ok",
        "service": "zephyr-mcp",
        "jira_base_url": JIRA_BASE_URL,
        "rate_limit": f"{RATE_LIMIT_COUNT} requests per {RATE_LIMIT_WINDOW_SECONDS}s (per user/token)",
        "ssl_verify": JIRA_VERIFY_SSL,
        "timeout_seconds": JIRA_TIMEOUT,
    }

# ============================================================
# SERVER START
# ============================================================

if __name__ == "__main__":
    logger.info("=== Starting Zephyr MCP Server ===")
    logger.info(f"JIRA Base URL : {JIRA_BASE_URL}")
    logger.info(f"Port          : {PORT}")
    logger.info(f"Rate Limit    : {RATE_LIMIT_COUNT} req / {RATE_LIMIT_WINDOW_SECONDS}s")
    logger.info(f"SSL Verify    : {JIRA_VERIFY_SSL}")
    logger.info(f"Logs Dir      : {LOG_DIR}")
    mcp.run(transport="http", host="0.0.0.0", port=PORT)
