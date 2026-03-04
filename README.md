# Zephyr MCP Server

A modular [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server for **Zephyr Scale (Jira Data Center)**. Enables LLMs to manage the full QA lifecycle — test cases, steps, cycles, and execution results — via a rate-limited, authenticated HTTP interface.

**Author:** harshit.singh@nomura.com

---

## Features

- **Full QA Lifecycle** — Create tests, manage steps, organise cycles, record execution results, attach files.
- **Resources + Tools** — Read-only operations exposed as MCP Resources (`zephyr://...`); writes as MCP Tools.
- **Dual Authentication** — Bearer Token (`Authorization: Bearer <token>`) or Basic Auth (`username` / `password` headers).
- **Sliding Window Rate Limiter** — Configurable per-user request throttling to prevent abuse.
- **Detailed Logging** — `logs/server.log` for system events, `logs/usage.log` for audit trail.
- **SSL Verify Off** — Designed for internal Jira Data Center instances (configurable).

---

## Project Structure

```text
zephyr-mcp/
├── main.py                  # Entry point (run from project root)
├── requirements.txt
├── README.md
├── logs/                    # Auto-created — server.log, usage.log
└── src/
    ├── __init__.py
    ├── config.py            # All configuration variables
    ├── middleware/
    │   ├── __init__.py
    │   └── rate_limit.py    # Sliding window RateLimiter
    └── tools/
        ├── __init__.py
        ├── tests.py         # Test case tools + resources
        ├── cycles.py        # Cycle management tools + resources
        └── executions.py    # Execution tools + resources
```

---

## Installation

```bash
pip install -r requirements.txt
```

---

## Configuration

All values are read from environment variables with sensible defaults. Edit `src/config.py` or export variables before starting:

| Variable | Default | Description |
|---|---|---|
| `JIRA_BASE_URL` | `http://stg-jira.nomura.com` | Jira Data Center base URL |
| `PORT` | `5000` | Port for the MCP HTTP server |
| `JIRA_TIMEOUT` | `30` | HTTP request timeout in seconds |
| `JIRA_VERIFY_SSL` | `False` | Set to `True` to enable SSL verification |
| `RATE_LIMIT_COUNT` | `5` | Max requests per window per user |
| `RATE_LIMIT_WINDOW_SECONDS` | `10` | Rate limit window duration in seconds |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

---

## Running the Server

Start from the **project root** (not inside `src/`):

```bash
python main.py
```

Or with environment variable overrides:

```bash
JIRA_BASE_URL=https://jira.yourcompany.com PORT=8080 python main.py
```

---

## Authentication

Every tool call must include credentials in the HTTP request headers.

**Option 1 — Bearer Token:**
```
Authorization: Bearer <your_jira_token>
```

**Option 2 — Basic Auth (dedicated headers):**
```
username: <jira_username>
password: <jira_password>
```

> [!IMPORTANT]
> If no credentials are provided, the server returns: `Credentials not provided`.
> Do **not** retry without correcting your headers.

---

## Rate Limiting

This server uses a **sliding window rate limiter** per user/token:

- Default: **5 requests per 10 seconds**
- Configurable via `RATE_LIMIT_COUNT` and `RATE_LIMIT_WINDOW_SECONDS`
- If exceeded, response: `Rate limit exceeded: max 5 requests per 10 seconds. Please wait 10 seconds.`
- **Use bulk tools** (`add_test_cases_to_cycle`, `bulk_execute_tests`) to minimise calls.

---

## MCP Resources (Read-Only)

Resources do not change state. Use them for discovery before invoking write tools.

| Resource URI | Description |
|---|---|
| `zephyr://system/projects` | List all accessible Jira projects |
| `zephyr://project/{project_key}/tests` | List test issues in a project |
| `zephyr://test/{issue_id}/steps` | View all steps for a test |
| `zephyr://version/{project_id}/{version_id}/cycles` | List cycles in a version |
| `zephyr://cycle/{cycle_id}/project/{project_id}/executions` | List executions with status |
| `zephyr://execution/{execution_id}/steps` | View step-level results |

---

## MCP Tools (Write Operations)

### 🧪 Test Case Management
| Tool | Description |
|---|---|
| `health_check` | Verify server is running and see config |
| `create_test_case` | Create a new Jira Test issue |
| `create_shared_test` | Create a reusable test (auto-prefixed `[SHARED]`) |
| `delete_test` | Permanently delete a Test issue |
| `update_jira_status` | Transition issue workflow status |
| `add_test_cases_to_cycle` | Bulk assign tests to a cycle |
| `insert_test_step` | Add a step at a specific position |
| `update_test_step` | Edit an existing step |
| `delete_test_step` | Remove a step |
| `get_test_steps` | Fetch steps as structured data |

### 🔄 Cycle Management
| Tool | Description |
|---|---|
| `get_projects` | List projects as structured data |
| `get_cycles` | List cycles as structured data |
| `fetch_cycle_stats` | Pass/Fail/WIP breakdown for a cycle |
| `get_issue_statuses` | Workflow transitions for a project |
| `create_cycle` | Create a new test cycle |
| `clone_cycle` | Copy an existing cycle |
| `edit_cycle` | Update cycle metadata |
| `delete_cycle` | Permanently remove a cycle |
| `add_folder` | Create a grouping folder within a cycle |

### ✅ Execution & Results
| Tool | Description |
|---|---|
| `get_executions_by_cycle` | List executions as structured data |
| `get_step_execution_details` | List step results as structured data |
| `get_execution_link` | Generate a browser link to an execution |
| `execute_test` | Record Pass/Fail/WIP/Blocked for an execution |
| `bulk_execute_tests` | Update multiple executions at once |
| `update_step_status` | Set Pass/Fail on a specific step result |
| `assign_test_to_cycle` | Assign a single test to a cycle |
| `add_attachment_to_execution` | Attach a file to an execution |
| `add_attachment_to_step_result` | Attach a file to a step result |

---

## Logging

| File | Content |
|---|---|
| `logs/server.log` | Server startup, errors, system events |
| `logs/usage.log` | Audit trail: timestamp, tool/resource name, parameters |

Log format: `2026-03-04T15:30:00 | tool=execute_test | params={'executionId': 123}`
