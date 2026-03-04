from typing import Any, Dict, List, Annotated, Optional
from pydantic import Field
from src.client.zephyr_client import ZephyrClient
from src.middleware.rate_limit import RateLimiter
from src.middleware.auth import get_auth_from_headers
from src.utils.logging_utils import log_access

def register_test_tools(mcp, limiter: RateLimiter):
    
    def get_client(ctx):
        headers = ctx.request.headers if ctx and hasattr(ctx, 'request') else {}
        username, password, token = get_auth_from_headers(headers)
        return ZephyrClient(username=username, password=password, token=token), (token or username or "anonymous"), headers

    @mcp.tool()
    async def create_test_case(
        ctx: Any,
        project_key: Annotated[str, Field(description="The unique key of the Jira project where the test will be created (e.g., 'PROJ')")],
        summary: Annotated[str, Field(description="Short, descriptive summary of the test case functionality")],
        description: Annotated[Optional[str], Field(description="Detailed steps, prerequisites, or context for this test", default="")] = "",
    ) -> Dict[str, Any]:
        """Create a new Jira issue of type 'Test'.
        
        This tool initializes a test case in Jira. Once created, you can add steps using 'add_test_step'.
        Output: A JSON object containing the new issue key, ID, and self-link.
        """
        client, user_id, headers = get_client(ctx)
        if not limiter.is_allowed(user_id):
            raise Exception("Rate limit exceeded for Zephyr MCP. Please wait approximately 10 seconds before retrying this operation.")
        
        log_access(user_id, "create_test_case", {"projectKey": project_key, "summary": summary})
        return await client.create_test_case(project_key, summary, description)

    @mcp.tool()
    async def add_test_cases(
        ctx: Any,
        cycle_id: Annotated[str, Field(description="The unique ID of the target Zephyr test cycle (e.g. '102')")],
        project_id: Annotated[int, Field(description="The numeric Jira project ID")],
        version_id: Annotated[int, Field(description="The numeric Jira version/release ID")],
        issue_ids: Annotated[List[int], Field(description="A list of numeric Jira issue IDs to be assigned to the cycle")],
    ) -> Dict[str, Any]:
        """Bulk assign multiple existing test cases to a specific test cycle.
        
        This facilitates grouping multiple tests for execution within a release milestone.
        Output: Confirmation showing complexity of the bulk assignment.
        """
        client, user_id, headers = get_client(ctx)
        if not limiter.is_allowed(user_id):
            raise Exception("Rate limit exceeded for Zephyr MCP. Please wait before attempting another bulk assignment.")
            
        log_access(user_id, "add_test_cases", {"cycleId": cycle_id, "issue_count": len(issue_ids)})
        return await client.add_test_cases_to_cycle(cycle_id, project_id, version_id, issue_ids)

    @mcp.tool()
    async def update_jira_status(
        ctx: Any,
        issue_key: Annotated[str, Field(description="The Jira issue key (e.g., 'QA-123')")],
        transition_id: Annotated[int, Field(description="The specific numeric ID of the workflow transition to perform (e.g., 21 for 'Pass')")],
    ) -> Dict[str, Any]:
        """Update the workflow status of a specific Jira issue.
        
        This tool directly interacts with Jira's issue transition system.
        Output: Empty object on success, or detailed error if the transition is invalid for the current state.
        """
        client, user_id, headers = get_client(ctx)
        if not limiter.is_allowed(user_id):
            raise Exception("Rate limit exceeded for Zephyr MCP. Jira status updates are throttled.")
            
        log_access(user_id, "update_jira_status", {"issueKey": issue_key, "transitionId": transition_id})
        return await client.update_jira_status(issue_key, transition_id)

    @mcp.tool()
    async def fetch_test_steps(
        ctx: Any,
        issue_id: Annotated[str, Field(description="The ID of the Jira issue representing the test")],
    ) -> List[Dict[str, Any]]:
        """Fetch all defined steps for a Zephyr test case."""
        client, user_id, headers = get_client(ctx)
        if not limiter.is_allowed(user_id):
            raise Exception("Rate limit exceeded.")
            
        log_access(user_id, "fetch_test_steps", {"issueId": issue_id})
        return await client.get_test_steps(issue_id)

    @mcp.tool()
    async def insert_test_steps(
        ctx: Any,
        issue_id: Annotated[str, Field(description="The ID of the Jira issue")],
        step: Annotated[str, Field(description="The action description for this step")],
        order_id: Annotated[int, Field(description="The position to insert at (1-indexed)")],
        data: Annotated[Optional[str], Field(description="Optional: Test data for this step", default="")] = "",
        result: Annotated[Optional[str], Field(description="Optional: Expected result", default="")] = "",
    ) -> Dict[str, Any]:
        """Insert a new test step at a specific position within a test."""
        client, user_id, headers = get_client(ctx)
        if not limiter.is_allowed(user_id):
            raise Exception("Rate limit exceeded.")
            
        log_access(user_id, "insert_test_steps", {"issueId": issue_id, "order": order_id})
        return await client.insert_test_step(issue_id, step, order_id, data, result)

    @mcp.tool()
    async def update_test_step(
        ctx: Any,
        issue_id: Annotated[str, Field(description="The Jira issue ID")],
        step_id: Annotated[int, Field(description="The unique Zephyr step ID")],
        step: Annotated[str, Field(description="Updated action description")],
        data: Annotated[Optional[str], Field(description="Updated test data", default="")] = "",
        result: Annotated[Optional[str], Field(description="Updated expected result", default="")] = "",
    ) -> Dict[str, Any]:
        """Update the content of an existing test step."""
        client, user_id, headers = get_client(ctx)
        if not limiter.is_allowed(user_id):
            raise Exception("Rate limit exceeded.")
            
        log_access(user_id, "update_test_step", {"issueId": issue_id, "stepId": step_id})
        return await client.update_test_step(issue_id, step_id, step, data, result)

    @mcp.tool()
    async def delete_test_step(
        ctx: Any,
        issue_id: Annotated[str, Field(description="The ID of the Jira issue")],
        step_id: Annotated[int, Field(description="The Zephyr step ID to remove")],
    ) -> Dict[str, Any]:
        """Delete a specific step from a test case."""
        client, user_id, headers = get_client(ctx)
        if not limiter.is_allowed(user_id):
            raise Exception("Rate limit exceeded.")
            
        log_access(user_id, "delete_test_step", {"issueId": issue_id, "stepId": step_id})
        return await client.delete_test_step(issue_id, step_id)

    @mcp.tool()
    async def delete_test(
        ctx: Any,
        issue_key: Annotated[str, Field(description="The unique Jira key of the test issue to removepermanently (e.g., 'QA-999')")],
    ) -> Dict[str, Any]:
        """Permanently delete a Jira issue designated as a 'Test'.
        
        WARNING: This removes the issue, its history, steps, and associations from the system.
        Output: Confirmation status of the deletion.
        """
        client, user_id, headers = get_client(ctx)
        if not limiter.is_allowed(user_id):
            raise Exception("Rate limit exceeded for Zephyr MCP. Destructive operations like deletion are rate limited.")
            
        log_access(user_id, "delete_test", {"issueKey": issue_key})
        return await client.delete_test_case(issue_key)

    @mcp.tool()
    async def create_shared_test(
        ctx: Any,
        project_key: Annotated[str, Field(description="Jira project key")],
        summary: Annotated[str, Field(description="Test summary")],
        description: Annotated[Optional[str], Field(description="Description", default="")] = "",
    ) -> Dict[str, Any]:
        """Create a Test Case intended for shared use (with [SHARED] tag)."""
        client, user_id, headers = get_client(ctx)
        if not limiter.is_allowed(user_id):
            raise Exception("Rate limit exceeded.")
        
        tagged_summary = f"[SHARED] {summary}"
        log_access(user_id, "create_shared_test", {"projectKey": project_key})
        return await client.create_test_case(project_key, tagged_summary, description)
