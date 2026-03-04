from typing import Any, Dict, List, Annotated, Optional
import os
from pydantic import Field
from src.client.zephyr_client import ZephyrClient
from src.middleware.rate_limit import RateLimiter
from src.middleware.auth import get_auth_from_headers
from src.utils.logging_utils import log_access

def register_execution_tools(mcp, limiter: RateLimiter):
    
    def get_client(ctx):
        headers = ctx.request.headers if ctx and hasattr(ctx, 'request') else {}
        username, password, token = get_auth_from_headers(headers)
        return ZephyrClient(username=username, password=password, token=token), (token or username or "anonymous"), headers

    @mcp.tool()
    async def execute_test(
        ctx: Any,
        execution_id: Annotated[int, Field(description="The unique numeric ID of the test execution instance to update")],
        status_id: Annotated[int, Field(description="Desired result ID: 1 (Pass), 2 (Fail), 3 (WIP), 4 (Blocked), -1 (Unexecuted)")],
        comment: Annotated[Optional[str], Field(description="Brief text explaining the testing outcome or failure details", default="")] = "",
    ) -> Dict[str, Any]:
        """Record the final testing outcome for a specific test execution in Zephyr.
        
        This updates the 'Validation' result for a test case assigned to a cycle.
        Output: A confirmation object including the updated execution status and timestamp.
        """
        client, user_id, headers = get_client(ctx)
        if not limiter.is_allowed(user_id):
            raise Exception("Rate limit exceeded for Zephyr MCP. Validation updates are throttled to ensure stability.")
        
        log_access(user_id, "execute_test", {"executionId": execution_id, "statusId": status_id})
        return await client.update_execution_status(execution_id, status_id, comment)

    @mcp.tool()
    async def fetch_step_execution_details(
        ctx: Any,
        execution_id: Annotated[int, Field(description="The execution ID to fetch step results for")],
    ) -> List[Dict[str, Any]]:
        """Fetch granular step-by-step execution details for a specific test run."""
        client, user_id, headers = get_client(ctx)
        if not limiter.is_allowed(user_id):
            raise Exception("Rate limit exceeded.")
            
        log_access(user_id, "fetch_step_execution_details", {"executionId": execution_id})
        return await client.get_step_execution_details(execution_id)

    @mcp.tool()
    async def update_step_status(
        ctx: Any,
        step_result_id: Annotated[int, Field(description="The unique Zephyr step result ID")],
        status_id: Annotated[int, Field(description="Status ID: 1=Pass, 2=Fail, 3=WIP, 4=Blocked")],
        comment: Annotated[Optional[str], Field(description="Optional: Comment for this specific step result", default="")] = "",
    ) -> Dict[str, Any]:
        """Update the validation status of a specific step within a test execution."""
        client, user_id, headers = get_client(ctx)
        if not limiter.is_allowed(user_id):
            raise Exception("Rate limit exceeded.")
            
        log_access(user_id, "update_step_status", {"stepResultId": step_result_id, "statusId": status_id})
        return await client.update_step_status(step_result_id, status_id, comment)

    @mcp.tool()
    async def add_attachment_to_execution(
        ctx: Any,
        execution_id: Annotated[int, Field(description="The execution ID to attach the file to")],
        file_path: Annotated[str, Field(description="The absolute local path to the file to upload")],
    ) -> Dict[str, Any]:
        """Add an attachment (screenshot, logs) to a general test execution result."""
        client, user_id, headers = get_client(ctx)
        if not limiter.is_allowed(user_id):
            raise Exception("Rate limit exceeded.")
            
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Attachment file not found: {file_path}")

        log_access(user_id, "add_attachment_to_execution", {"executionId": execution_id, "file": file_path})
        return await client.add_attachment_to_execution(execution_id, file_path)

    @mcp.tool()
    async def add_attachment_to_step_result(
        ctx: Any,
        step_result_id: Annotated[int, Field(description="The step result ID to attach the file to")],
        file_path: Annotated[str, Field(description="The absolute local path to the file to upload")],
    ) -> Dict[str, Any]:
        """Add an attachment to a specific step's result within an execution."""
        client, user_id, headers = get_client(ctx)
        if not limiter.is_allowed(user_id):
            raise Exception("Rate limit exceeded.")
            
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Attachment file not found: {file_path}")

        log_access(user_id, "add_attachment_to_step_result", {"stepResultId": step_result_id, "file": file_path})
        return await client.add_attachment_to_step_result(step_result_id, file_path)

    @mcp.tool()
    async def bulk_execute_tests(
        ctx: Any,
        execution_ids: Annotated[List[int], Field(description="List of execution IDs to update")],
        status_id: Annotated[int, Field(description="Target status ID")],
        comment: Annotated[Optional[str], Field(description="Comment for all executions", default="")] = "",
    ) -> Dict[str, Any]:
        """Bulk update multiple test executions with a single result."""
        client, user_id, headers = get_client(ctx)
        if not limiter.is_allowed(user_id):
            raise Exception("Rate limit exceeded.")
        
        log_access(user_id, "bulk_execute_tests", {"count": len(execution_ids)})
        return await client.bulk_update_status(execution_ids, status_id, comment)

    @mcp.tool()
    async def get_execution_link(
        ctx: Any,
        execution_id: Annotated[int, Field(description="Execution ID")],
    ) -> str:
        """Generate a direct web link to the Zephyr execution report page."""
        client, user_id, headers = get_client(ctx)
        log_access(user_id, "get_execution_link", {"executionId": execution_id})
        return client.get_execution_link(execution_id)

    @mcp.tool()
    async def assign_test_to_cycle(
        ctx: Any,
        issue_id: Annotated[int, Field(description="Jira issue ID of the test")],
        cycle_id: Annotated[int, Field(description="Zephyr cycle ID")],
        project_id: Annotated[int, Field(description="Project ID")],
        version_id: Annotated[int, Field(description="Version ID")],
    ) -> Dict[str, Any]:
        """Assign an existing test case to a specific cycle (Create execution)."""
        client, user_id, headers = get_client(ctx)
        if not limiter.is_allowed(user_id):
            raise Exception("Rate limit exceeded.")
            
        log_access(user_id, "assign_test_to_cycle", {"issueId": issue_id, "cycleId": cycle_id})
        return await client.create_execution(issue_id, cycle_id, project_id, version_id)

    @mcp.tool()
    async def get_executions_by_cycle(
        ctx: Any,
        cycle_id: Annotated[int, Field(description="Cycle ID")],
        project_id: Annotated[int, Field(description="Project ID")],
    ) -> List[Dict[str, Any]]:
        """Fetch all test executions and their current results for a cycle."""
        client, user_id, headers = get_client(ctx)
        if not limiter.is_allowed(user_id):
            raise Exception("Rate limit exceeded.")
            
        log_access(user_id, "get_executions_by_cycle", {"cycleId": cycle_id})
        return await client.get_executions_by_cycle(cycle_id, project_id)
