import os
from typing import Any, Dict, List, Optional
from fastmcp import FastMCP
from fastmcp.server.context import Context


def register_execution_tools(mcp, JIRA_API_URL, ZAPI_BASE_URL, log_usage, extract_zephyr_auth, check_rate_limit, zephyr_request, zephyr_upload):
    """Register all test execution management tools and resources."""

    # ============================================================
    # RESOURCES — read-only
    # ============================================================

    @mcp.resource("zephyr://cycle/{cycle_id}/project/{project_id}/executions")
    async def list_executions(cycle_id: str, project_id: str, ctx: Context) -> str:
        """
        [RESOURCE] List all test executions and their current results for a cycle.

        URI: zephyr://cycle/{cycle_id}/project/{project_id}/executions
        - cycle_id: Numeric Zephyr cycle ID
        - project_id: Numeric Jira project ID

        Returns a formatted list showing execution ID, issue key, and current result status.
        Use execution IDs from this list to update results via execute_test.
        """
        check_rate_limit(ctx)
        log_usage("resource", "list_executions", {"cycleId": cycle_id, "projectId": project_id})
        username, password, token = extract_zephyr_auth(ctx)

        result = await zephyr_request(
            "GET", f"{ZAPI_BASE_URL}/execution",
            username, password, token,
            params={"cycleId": cycle_id, "projectId": project_id}
        )

        executions = result.get("executions", [])
        lines = [f"Executions for Cycle {cycle_id} ({len(executions)} total):"]
        status_map = {"-1": "UNEXECUTED", "1": "PASS", "2": "FAIL", "3": "WIP", "4": "BLOCKED"}
        for e in executions:
            status_label = status_map.get(str(e.get("executionStatus", "-1")), "UNKNOWN")
            lines.append(f"- Exe ID: {e.get('id')} | Issue: {e.get('issueKey')} | Status: {status_label}")
        return "\n".join(lines)

    @mcp.resource("zephyr://execution/{execution_id}/steps")
    async def list_step_results(execution_id: str, ctx: Context) -> str:
        """
        [RESOURCE] Fetch step-by-step execution results for a specific test run.

        URI: zephyr://execution/{execution_id}/steps
        - execution_id: Numeric Zephyr execution ID

        Returns each step's action, result, and current pass/fail status.
        Use step_result_id values from this response with update_step_status.
        """
        check_rate_limit(ctx)
        log_usage("resource", "list_step_results", {"executionId": execution_id})
        username, password, token = extract_zephyr_auth(ctx)

        results = await zephyr_request("GET", f"{ZAPI_BASE_URL}/stepResult?executionId={execution_id}", username, password, token)

        status_map = {"-1": "UNEXECUTED", "1": "PASS", "2": "FAIL", "3": "WIP", "4": "BLOCKED"}
        lines = [f"Step Results for Execution {execution_id}:"]
        for s in (results if isinstance(results, list) else []):
            status_label = status_map.get(str(s.get("status", "-1")), "UNKNOWN")
            lines.append(f"\nStep Result ID: {s.get('id')} | Order: {s.get('orderId')} | Status: {status_label}")
            lines.append(f"  Action : {s.get('step', '')}")
            lines.append(f"  Comment: {s.get('comment', '')}")
        return "\n".join(lines)

    # ============================================================
    # TOOLS — write operations
    # ============================================================

    @mcp.tool()
    async def get_executions_by_cycle(
        ctx: Context,
        cycle_id: int,
        project_id: int,
    ) -> List[Dict[str, Any]]:
        """
        Fetch all test executions and their current results for a cycle (as structured data).

        Use this when you need machine-readable execution data for programmatic processing.
        For a human-readable summary, use zephyr://cycle/{cycle_id}/project/{project_id}/executions resource.

        Input:
        - cycle_id (required): Numeric Zephyr cycle ID. Use get_cycles to find.
        - project_id (required): Numeric Jira project ID.

        Output: List of execution objects with id, issueKey, executionStatus fields.
        Status codes: -1=UNEXECUTED, 1=PASS, 2=FAIL, 3=WIP, 4=BLOCKED

        Errors:
        - 404: Cycle or project not found.
        """
        check_rate_limit(ctx)
        log_usage("tool", "get_executions_by_cycle", {"cycleId": cycle_id, "projectId": project_id})
        username, password, token = extract_zephyr_auth(ctx)

        result = await zephyr_request(
            "GET", f"{ZAPI_BASE_URL}/execution",
            username, password, token,
            params={"cycleId": cycle_id, "projectId": project_id}
        )
        return result.get("executions", [])

    @mcp.tool()
    async def get_execution_link(
        ctx: Context,
        execution_id: int,
    ) -> str:
        """
        Generate a direct browser URL to the Zephyr execution report page.

        Use this to provide the user with a clickable link to view the detailed execution report in Jira.

        Input:
        - execution_id (required): Numeric Zephyr execution ID.

        Output: A URL string pointing to the execution in Jira's Zephyr interface.
        """
        check_rate_limit(ctx)
        log_usage("tool", "get_execution_link", {"executionId": execution_id})
        extract_zephyr_auth(ctx)  # validate credentials only
        base = JIRA_API_URL.replace("/rest/api/2", "")
        return f"{base}/secure/Tests.jspa#/design?executionId={execution_id}"

    @mcp.tool()
    async def execute_test(
        ctx: Context,
        execution_id: int,
        status_id: int,
        comment: str = "",
    ) -> Dict[str, Any]:
        """
        Record the final testing outcome for a specific test execution.

        Use this after running a test manually or via automation to record the result.
        First call get_executions_by_cycle to find the execution_id for the test you ran.

        Input:
        - execution_id (required): Numeric Zephyr execution ID.
        - status_id (required): Execution result:
            1 = PASS     — Test passed all assertions
            2 = FAIL     — Test failed one or more checks
            3 = WIP      — Test is in progress (not finished)
            4 = BLOCKED  — Cannot run due to a blocking issue
           -1 = UNEXECUTED — Reset to unexecuted state
        - comment (optional): Brief explanation of result (especially useful for FAIL/BLOCKED).

        Output: Updated execution object from Zephyr.

        Errors:
        - 400: Invalid status_id value.
        - 404: Execution ID not found.
        """
        check_rate_limit(ctx)
        log_usage("tool", "execute_test", {"executionId": execution_id, "statusId": status_id})
        username, password, token = extract_zephyr_auth(ctx)

        payload = {"status": str(status_id), "comment": comment}
        return await zephyr_request("PUT", f"{ZAPI_BASE_URL}/execution/{execution_id}/execute", username, password, token, json_data=payload)

    @mcp.tool()
    async def bulk_execute_tests(
        ctx: Context,
        execution_ids: List[int],
        status_id: int,
        comment: str = "",
    ) -> Dict[str, Any]:
        """
        Bulk update multiple test executions with a single result status.

        RATE LIMIT FRIENDLY: Use this instead of calling execute_test in a loop.
        This counts as ONE API call regardless of how many executions you update.

        Typical use: After a regression run, mark all passed tests as PASS in one call.

        Input:
        - execution_ids (required): List of numeric Zephyr execution IDs to update.
        - status_id (required): Target status for ALL executions: 1=PASS, 2=FAIL, 3=WIP, 4=BLOCKED, -1=UNEXECUTED
        - comment (optional): Comment applied to all updated executions.

        Output: Bulk update confirmation from Zephyr.

        Errors:
        - 400: Invalid status_id or malformed execution_ids list.
        """
        check_rate_limit(ctx)
        log_usage("tool", "bulk_execute_tests", {"count": len(execution_ids), "statusId": status_id})
        username, password, token = extract_zephyr_auth(ctx)

        payload = {"executions": execution_ids, "status": str(status_id), "comment": comment}
        return await zephyr_request("PUT", f"{ZAPI_BASE_URL}/execution/updateBulkStatus", username, password, token, json_data=payload)

    @mcp.tool()
    async def get_step_execution_details(
        ctx: Context,
        execution_id: int,
    ) -> List[Dict[str, Any]]:
        """
        Fetch granular step-by-step execution results for a test run (as structured data).

        Use this when you need to programmatically process or report on step-level results.
        For a human-readable view, use zephyr://execution/{execution_id}/steps resource.
        Use step result IDs from this output with update_step_status.

        Input:
        - execution_id (required): Numeric Zephyr execution ID.

        Output: List of step result objects with id, orderId, status, step, comment.
        Status: -1=UNEXECUTED, 1=PASS, 2=FAIL, 3=WIP, 4=BLOCKED
        """
        check_rate_limit(ctx)
        log_usage("tool", "get_step_execution_details", {"executionId": execution_id})
        username, password, token = extract_zephyr_auth(ctx)
        return await zephyr_request("GET", f"{ZAPI_BASE_URL}/stepResult?executionId={execution_id}", username, password, token)

    @mcp.tool()
    async def update_step_status(
        ctx: Context,
        step_result_id: int,
        status_id: int,
        comment: str = "",
    ) -> Dict[str, Any]:
        """
        Update the pass/fail result of a specific step within a running test execution.

        Use this for granular step-level reporting when individual steps need different statuses.
        Get step_result_id from get_step_execution_details or the zephyr://execution/{id}/steps resource.

        Input:
        - step_result_id (required): Numeric Zephyr step result ID (NOT the step definition ID).
        - status_id (required): Step result: 1=PASS, 2=FAIL, 3=WIP, 4=BLOCKED, -1=UNEXECUTED
        - comment (optional): Notes on why this step passed or failed.

        Output: Updated step result object.

        Errors:
        - 404: Step result ID not found.
        """
        check_rate_limit(ctx)
        log_usage("tool", "update_step_status", {"stepResultId": step_result_id, "statusId": status_id})
        username, password, token = extract_zephyr_auth(ctx)

        payload = {"status": str(status_id), "comment": comment}
        return await zephyr_request("PUT", f"{ZAPI_BASE_URL}/stepResult/{step_result_id}", username, password, token, json_data=payload)

    @mcp.tool()
    async def assign_test_to_cycle(
        ctx: Context,
        issue_id: int,
        cycle_id: int,
        project_id: int,
        version_id: int,
    ) -> Dict[str, Any]:
        """
        Assign a single test to a cycle by creating an execution record.

        Use add_test_cases_to_cycle for bulk assignment (more rate-limit friendly).
        This tool is for assigning one test at a time.

        Input:
        - issue_id (required): Numeric Jira issue ID (the number, not 'QA-123').
        - cycle_id (required): Numeric Zephyr cycle ID.
        - project_id (required): Numeric Jira project ID.
        - version_id (required): Numeric Jira version ID.

        Output: Created execution object with execution_id for future status updates.

        Errors:
        - 400: Invalid IDs or test already exists in this cycle.
        - 404: Issue, cycle, or version not found.
        """
        check_rate_limit(ctx)
        log_usage("tool", "assign_test_to_cycle", {"issueId": issue_id, "cycleId": cycle_id})
        username, password, token = extract_zephyr_auth(ctx)

        payload = {"issueId": issue_id, "cycleId": cycle_id, "projectId": project_id, "versionId": version_id}
        return await zephyr_request("POST", f"{ZAPI_BASE_URL}/execution", username, password, token, json_data=payload)

    @mcp.tool()
    async def add_attachment_to_execution(
        ctx: Context,
        execution_id: int,
        file_path: str,
    ) -> Dict[str, Any]:
        """
        Attach a file (screenshot, log, report) to a test execution result.

        Use this to provide evidence of test results directly in Zephyr.
        The file must be accessible on the local filesystem where the server is running.

        Input:
        - execution_id (required): Numeric Zephyr execution ID.
        - file_path (required): Absolute local file path to the file to attach.
          Example: 'C:/test_results/screenshot.png'

        Output: Attachment confirmation from Zephyr.

        Errors:
        - FileNotFoundError: file_path does not exist on the server's filesystem.
        - 400: Unsupported file type or file too large.
        - 404: Execution not found.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(
                f"Attachment file not found at path: {file_path}. "
                "Ensure the file exists on the server's local filesystem."
            )

        check_rate_limit(ctx)
        log_usage("tool", "add_attachment_to_execution", {"executionId": execution_id, "file": file_path})
        username, password, token = extract_zephyr_auth(ctx)

        with open(file_path, "rb") as f:
            file_name = os.path.basename(file_path)
            files = {"file": (file_name, f, "application/octet-stream")}
            return await zephyr_upload(
                f"{ZAPI_BASE_URL}/attachment?entityId={execution_id}&entityType=EXECUTION",
                files, username, password, token
            )

    @mcp.tool()
    async def add_attachment_to_step_result(
        ctx: Context,
        step_result_id: int,
        file_path: str,
    ) -> Dict[str, Any]:
        """
        Attach a file to a specific step's result within an execution.

        Use this when you need step-level evidence (e.g. screenshot of a specific assertion failure).
        Get step_result_id from get_step_execution_details first.

        Input:
        - step_result_id (required): Numeric Zephyr step result ID.
        - file_path (required): Absolute local file path to the file to attach.

        Output: Attachment confirmation from Zephyr.

        Errors:
        - FileNotFoundError: file_path does not exist on the server's filesystem.
        - 404: Step result not found.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(
                f"Attachment file not found at path: {file_path}. "
                "Ensure the file exists on the server's local filesystem."
            )

        check_rate_limit(ctx)
        log_usage("tool", "add_attachment_to_step_result", {"stepResultId": step_result_id})
        username, password, token = extract_zephyr_auth(ctx)

        with open(file_path, "rb") as f:
            file_name = os.path.basename(file_path)
            files = {"file": (file_name, f, "application/octet-stream")}
            return await zephyr_upload(
                f"{ZAPI_BASE_URL}/attachment?entityId={step_result_id}&entityType=STEP_RESULT",
                files, username, password, token
            )
