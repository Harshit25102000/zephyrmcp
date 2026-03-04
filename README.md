# Zephyr MCP Server

A robust and modular Model Context Protocol (MCP) server for Zephyr (Jira Data Center). This server provides a comprehensive toolset for QA and release management, allowing LLMs to manage test cases, test steps, cycles, and executions.

# Author
- harshit.singh@nomura.com

## Features

- **Full QA Lifecycle**: Support for creating tests, managing steps, grouping by cycles, and recording execution results.
- **UI Parity Tools**: Advanced tools for bulk execution, cycle cloning (Convert to Regression), and shareable execution link generation.
- **Modular Architecture**: Separate packages for `client` (ZAPI interaction), `middleware` (Auth & Rate Limiting), `tools` (MCP interface), and `utils`.
- **Dual Authentication**: Supports both **Basic Auth** (Username/Password) and **Token Auth** (Bearer Token) passed via headers.
- **Advanced Rate Limiting**: Sliding window rate limiter to prevent misuse and ensure stay within API quotas.
- **Detailed Logging**: 
    - `logs/access.log`: Audit trail of tool usage (who called what with which parameters).
    - `logs/server.log`: System events, errors, and debugging information.
- **HTTP/SSE Transport**: Runs in streamable HTTP mode for easy integration.

## Project Structure

```text
zephyr-mcp/
├── src/
│   ├── main.py             # Server entry point
│   ├── config.py           # Configuration variables
│   ├── client/             # Modular Zephyr/Jira client
│   │   ├── base.py
│   │   ├── tests.py
│   │   ├── cycles.py
│   │   └── executions.py
│   ├── tools/              # Modular MCP tool definitions
│   │   ├── tests.py
│   │   ├── cycles.py
│   │   └── executions.py
│   ├── middleware/         # Auth and Rate Limiting
│   └── utils/              # Logging and factory utilities
├── logs/                   # (Auto-created) log files
├── requirements.txt
└── README.md
```

## Installation

1. Clone the repository to your local machine.
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

Modify `src/config.py` or set environment variables to configure the server:

- `JIRA_BASE_URL`: The URL of your Jira Data Center instance.
- `PORT`: The port the MCP server will listen on (default: 9002).
- `RATE_LIMIT_COUNT`: Number of requests allowed per window.
- `RATE_LIMIT_WINDOW_SECONDS`: The timeframe for the rate limit window.
- `MAX_PROJECTS_PER_QUERY` / `MAX_TESTS_PER_BULK`: Safety guardrails for bulk operations.

## Running the Server

Start the MCP server in HTTP mode:

```bash
python src/main.py
```

The server will start listening on the configured port. By default, it uses the `http` transport for streamable communication.

## Tool Overview

### 🧪 Test Case Management (`src/tools/tests.py`)
- **`create_test_case`**: Initializes a new Jira issue of type 'Test'. (Req: `project_key`, `summary`).
- **`add_test_cases`**: Bulk assign existing tests to a cycle. (Req: `cycle_id`, `project_id`, `version_id`, `issue_ids`).
- **`update_jira_status`**: Transitions a test case through its Jira workflow. (Req: `issue_key`, `transition_id`).
- **`create_shared_test`**: Specialized creation of reusable test cases with `[SHARED]` prefix.
- **`fetch_test_steps`**: Retrieves the detailed ACTION/DATA/RESULT sequence for any test ID.
- **`insert_test_steps`**: Inserts a new step at a precise position within a test.
- **`update_test_step`**: Modifies the action or outcome of an existing step ID.
- **`delete_test_step`**: Removes a specific step from a test case.
- **`delete_test`**: Permanently deletes the Jira issue (test case) from the server.

### 🚲 Cycle & Release Management (`src/tools/cycles.py`)
- **`create_cycle`**: Create a test cycle with full metadata (Build, Env, Dates). (Req: `name`, `project_id`, `version_id`).
- **`clone_cycle`**: Efficiently copies an existing cycle's test associations into a new one.
- **`add_folder`**: Creates a logical folder within a cycle for granular grouping.
- **`edit_cycle`**: Updates attributes (name, environment, build) of an existing cycle ID.
- **`delete_cycle`**: Destructive operation to remove a cycle and all its execution data.
- **`fetch_cycles_from_version`**: Lists all active cycles for a specific release version ID.
- **`fetch_test_cases_from_cycle_with_stats`**: **Analytical tool** providing a Pass/Fail breakdown for every execution in a cycle.
- **`get_issue_statuses`**: Project-wide distribution of issue statuses for QA visibility.
- **`list_qa_projects`**: Lists all projects available for Zephyr integration.

### ✅ Execution & Validation (`src/tools/executions.py`)
- **`execute_test`**: Principal tool for recording Pass/Fail results for a test in a cycle.
- **`bulk_execute_tests`**: Simultaneously updates statuses for multiple executions.
- **`fetch_step_execution_details`**: Retrieves granular, step-by-step results for a validation run.
- **`update_step_status`**: Precisely records success/failure for an individual test step.
- **`add_attachment_to_execution`**: Attaches diagnostic files (logs/images) to a general execution record.
- **`add_attachment_to_step_result`**: Attaches proof files specifically to a failed test step.
- **`get_execution_link`**: Generates a shareable URL to the interactive Zephyr execution page in Jira.
- **`assign_test_to_cycle`**: Starts a validation run for a test by assigning it to a cycle.
- **`get_executions_by_cycle`**: Comprehensive list of all recorded results for a specific cycle ID.

## Authentication

Users must provide Jira credentials via the `Authorization` header in their MCP request:

- **Token Auth**: `Bearer <Jira_PAT>`
- **Basic Auth**: `Basic <Base64_Encoded_Credentials>`

The server automatically extracts these credentials to initialize the `ZephyrClient` per request.

## Logging

The server automatically creates a `logs/` directory:
- Every tool usage is logged in JSON format to `logs/access.log`.
- System-level logs are maintained in `logs/server.log`.
