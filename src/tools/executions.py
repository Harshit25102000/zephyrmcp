from typing import Any, Dict, List, Annotated, Optional
import os
from mcp.server.fastmcp import Context
from pydantic import Field
from src.utils.logging_utils import log_usage
from src.middleware.auth import extract_zephyr_auth
from src.client.zephyr_client import ZephyrClient

def register_execution_tools(mcp, limiter=None):

    # ============================================================
    # RESOURCES (Read Operations)
    # ============================================================

    @mcp.resource("zephyr://execution/{execution_id}/steps")
    async def fetch_step_execution_details(execution_id: int, ctx: Context) -> str:
        """Fetch granular step-by-step execution details for a specific test run."""
        log_usage("resource", "fetch_step_execution_details", {"executionId": execution_id})
        username, password, token = extract_zephyr_auth(ctx)
        client = ZephyrClient(username=username, password=password, token=token)
        steps = await client.get_step_execution_details(execution_id)
        
        output = [f"Execution Steps for ID {execution_id}:"]
        for s in steps:
            status = s.get('status', {}).get('name', 'Unknown')
            output.append(f"- Step {s.get('orderId')}: {status} | Comment: {s.get('comment')}")
        return "\n".join(output)

    @mcp.resource("zephyr://execution/{execution_id}/link")
    async def get_execution_link(execution_id: int, ctx: Context) -> str:
        """Generate a direct web link to the Zephyr execution report page."""
        log_usage("resource", "get_execution_link", {"executionId": execution_id})
        username, password, token = extract_zephyr_auth(ctx)
        client = ZephyrClient(username=username, password=password, token=token)
        return client.get_execution_link(execution_id)

    @mcp.resource("zephyr://cycle/{cycle_id}/project/{project_id}/executions")
    async def get_executions_by_cycle(cycle_id: int, project_id: int, ctx: Context) -> str:
        """Fetch all test executions and their current results for a cycle."""
        log_usage("resource", "get_executions_by_cycle", {"cycleId": cycle_id})
        username, password, token = extract_zephyr_auth(ctx)
        client = ZephyrClient(username=username, password=password, token=token)
        executions = await client.get_executions_by_cycle(cycle_id, project_id)
        
        output = [f"Executions for Cycle {cycle_id}:"]
        for e in executions.get("executions", []):
            output.append(f"- Exe ID: {e.get('id')} | Issue: {e.get('issueKey')} | Status: {e.get('executionStatusName')}")
        return "\n".join(output)

    # ============================================================
    # TOOLS (Write Operations)
    # ============================================================

    @mcp.tool()
    async def execute_test(
        ctx: Context,
        execution_id: Annotated[int, Field(description="The unique numeric ID of the test execution instance to update")],
        status_id: Annotated[int, Field(description="Desired result ID: 1 (Pass), 2 (Fail), 3 (WIP), 4 (Blocked), -1 (Unexecuted)")],
        comment: Annotated[Optional[str], Field(description="Brief text explaining the testing outcome or failure details", default="")] = "",
    ) -> Dict[str, Any]:
        """Record the final testing outcome for a specific test execution."""
        log_usage("tool", "execute_test", {"executionId": execution_id, "statusId": status_id})
        username, password, token = extract_zephyr_auth(ctx)
        client = ZephyrClient(username=username, password=password, token=token)
        return await client.update_execution_status(execution_id, status_id, comment)

    @mcp.tool()
    async def update_step_status(
        ctx: Context,
        step_result_id: Annotated[int, Field(description="The unique Zephyr step result ID")],
        status_id: Annotated[int, Field(description="Status ID: 1=Pass, 2=Fail, 3=WIP, 4=Blocked")],
        comment: Annotated[Optional[str], Field(description="Optional: Comment for this specific step result", default="")] = "",
    ) -> Dict[str, Any]:
        """Update the validation status of a specific step within a test execution."""
        log_usage("tool", "update_step_status", {"stepResultId": step_result_id, "statusId": status_id})
        username, password, token = extract_zephyr_auth(ctx)
        client = ZephyrClient(username=username, password=password, token=token)
        return await client.update_step_status(step_result_id, status_id, comment)

    @mcp.tool()
    async def add_attachment_to_execution(
        ctx: Context,
        execution_id: Annotated[int, Field(description="The execution ID to attach the file to")],
        file_path: Annotated[str, Field(description="The absolute local path to the file to upload")],
    ) -> Dict[str, Any]:
        """Add an attachment (screenshot, logs) to a general test execution result."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Attachment file not found: {file_path}")

        log_usage("tool", "add_attachment_to_execution", {"executionId": execution_id, "file": file_path})
        username, password, token = extract_zephyr_auth(ctx)
        client = ZephyrClient(username=username, password=password, token=token)
        return await client.add_attachment_to_execution(execution_id, file_path)

    @mcp.tool()
    async def add_attachment_to_step_result(
        ctx: Context,
        step_result_id: Annotated[int, Field(description="The step result ID to attach the file to")],
        file_path: Annotated[str, Field(description="The absolute local path to the file to upload")],
    ) -> Dict[str, Any]:
        """Add an attachment to a specific step's result within an execution."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Attachment file not found: {file_path}")

        log_usage("tool", "add_attachment_to_step_result", {"stepResultId": step_result_id, "file": file_path})
        username, password, token = extract_zephyr_auth(ctx)
        client = ZephyrClient(username=username, password=password, token=token)
        return await client.add_attachment_to_step_result(step_result_id, file_path)

    @mcp.tool()
    async def bulk_execute_tests(
        ctx: Context,
        execution_ids: Annotated[List[int], Field(description="List of execution IDs to update")],
        status_id: Annotated[int, Field(description="Target status ID")],
        comment: Annotated[Optional[str], Field(description="Comment for all executions", default="")] = "",
    ) -> Dict[str, Any]:
        """Bulk update multiple test executions with a single result."""
        log_usage("tool", "bulk_execute_tests", {"count": len(execution_ids)})
        username, password, token = extract_zephyr_auth(ctx)
        client = ZephyrClient(username=username, password=password, token=token)
        return await client.bulk_update_status(execution_ids, status_id, comment)

    @mcp.tool()
    async def assign_test_to_cycle(
        ctx: Context,
        issue_id: Annotated[int, Field(description="Jira issue ID of the test")],
        cycle_id: Annotated[int, Field(description="Zephyr cycle ID")],
        project_id: Annotated[int, Field(description="Project ID")],
        version_id: Annotated[int, Field(description="Version ID")],
    ) -> Dict[str, Any]:
        """Assign an existing test case to a specific cycle (Create execution)."""
        log_usage("tool", "assign_test_to_cycle", {"issueId": issue_id, "cycleId": cycle_id})
        username, password, token = extract_zephyr_auth(ctx)
        client = ZephyrClient(username=username, password=password, token=token)
        return await client.create_execution(issue_id, cycle_id, project_id, version_id)
