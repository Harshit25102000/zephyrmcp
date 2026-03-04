from typing import Any, Dict, List, Annotated, Optional
from mcp.server.fastmcp import Context
from pydantic import Field
from src.utils.logging_utils import log_usage
from src.middleware.auth import extract_zephyr_auth
from src.client.zephyr_client import ZephyrClient

def register_test_tools(mcp, limiter=None):
    
    # ============================================================
    # RESOURCES (Read Operations)
    # ============================================================

    @mcp.resource("zephyr://test/{issue_id}/steps")
    async def fetch_test_steps(issue_id: str, ctx: Context) -> str:
        """Fetch all defined steps for a Zephyr test case as a formatted string."""
        log_usage("resource", "fetch_test_steps", {"issueId": issue_id})
        username, password, token = extract_zephyr_auth(ctx)
        client = ZephyrClient(username=username, password=password, token=token)
        
        steps = await client.get_test_steps(issue_id)
        
        output = [f"Steps for Test {issue_id}:"]
        for s in steps:
            output.append(f"- Step {s.get('orderId')}: {s.get('step')}")
            if s.get('data'): output.append(f"  Data: {s.get('data')}")
            if s.get('result'): output.append(f"  Result: {s.get('result')}")
            
        return "\n".join(output)

    # ============================================================
    # TOOLS (Write Operations)
    # ============================================================

    @mcp.tool()
    async def create_test_case(
        ctx: Context,
        project_key: Annotated[str, Field(description="The unique key of the Jira project where the test will be created (e.g., 'PROJ')")],
        summary: Annotated[str, Field(description="Short, descriptive summary of the test case functionality")],
        description: Annotated[Optional[str], Field(description="Detailed steps, prerequisites, or context for this test", default="")] = "",
    ) -> Dict[str, Any]:
        """Create a new Jira issue of type 'Test'."""
        log_usage("tool", "create_test_case", {"projectKey": project_key, "summary": summary})
        username, password, token = extract_zephyr_auth(ctx)
        client = ZephyrClient(username=username, password=password, token=token)
        return await client.create_test_case(project_key, summary, description)

    @mcp.tool()
    async def add_test_cases(
        ctx: Context,
        cycle_id: Annotated[str, Field(description="The unique ID of the target Zephyr test cycle (e.g. '102')")],
        project_id: Annotated[int, Field(description="The numeric Jira project ID")],
        version_id: Annotated[int, Field(description="The numeric Jira version/release ID")],
        issue_ids: Annotated[List[int], Field(description="A list of numeric Jira issue IDs to be assigned to the cycle")],
    ) -> Dict[str, Any]:
        """Bulk assign multiple existing test cases to a specific test cycle."""
        log_usage("tool", "add_test_cases", {"cycleId": cycle_id, "issue_count": len(issue_ids)})
        username, password, token = extract_zephyr_auth(ctx)
        client = ZephyrClient(username=username, password=password, token=token)
        return await client.add_test_cases_to_cycle(cycle_id, project_id, version_id, issue_ids)

    @mcp.tool()
    async def update_jira_status(
        ctx: Context,
        issue_key: Annotated[str, Field(description="The Jira issue key (e.g., 'QA-123')")],
        transition_id: Annotated[int, Field(description="The specific numeric ID of the workflow transition to perform (e.g., 21 for 'Pass')")],
    ) -> Dict[str, Any]:
        """Update the workflow status of a specific Jira issue."""
        log_usage("tool", "update_jira_status", {"issueKey": issue_key, "transitionId": transition_id})
        username, password, token = extract_zephyr_auth(ctx)
        client = ZephyrClient(username=username, password=password, token=token)
        return await client.update_jira_status(issue_key, transition_id)

    @mcp.tool()
    async def insert_test_steps(
        ctx: Context,
        issue_id: Annotated[str, Field(description="The ID of the Jira issue")],
        step: Annotated[str, Field(description="The action description for this step")],
        order_id: Annotated[int, Field(description="The position to insert at (1-indexed)")],
        data: Annotated[Optional[str], Field(description="Optional: Test data for this step", default="")] = "",
        result: Annotated[Optional[str], Field(description="Optional: Expected result", default="")] = "",
    ) -> Dict[str, Any]:
        """Insert a new test step at a specific position within a test."""
        log_usage("tool", "insert_test_steps", {"issueId": issue_id, "order": order_id})
        username, password, token = extract_zephyr_auth(ctx)
        client = ZephyrClient(username=username, password=password, token=token)
        return await client.insert_test_step(issue_id, step, order_id, data, result)

    @mcp.tool()
    async def update_test_step(
        ctx: Context,
        issue_id: Annotated[str, Field(description="The Jira issue ID")],
        step_id: Annotated[int, Field(description="The unique Zephyr step ID")],
        step: Annotated[str, Field(description="Updated action description")],
        data: Annotated[Optional[str], Field(description="Updated test data", default="")] = "",
        result: Annotated[Optional[str], Field(description="Updated expected result", default="")] = "",
    ) -> Dict[str, Any]:
        """Update the content of an existing test step."""
        log_usage("tool", "update_test_step", {"issueId": issue_id, "stepId": step_id})
        username, password, token = extract_zephyr_auth(ctx)
        client = ZephyrClient(username=username, password=password, token=token)
        return await client.update_test_step(issue_id, step_id, step, data, result)

    @mcp.tool()
    async def delete_test_step(
        ctx: Context,
        issue_id: Annotated[str, Field(description="The ID of the Jira issue")],
        step_id: Annotated[int, Field(description="The Zephyr step ID to remove")],
    ) -> Dict[str, Any]:
        """Delete a specific step from a test case."""
        log_usage("tool", "delete_test_step", {"issueId": issue_id, "stepId": step_id})
        username, password, token = extract_zephyr_auth(ctx)
        client = ZephyrClient(username=username, password=password, token=token)
        return await client.delete_test_step(issue_id, step_id)

    @mcp.tool()
    async def delete_test(
        ctx: Context,
        issue_key: Annotated[str, Field(description="The unique Jira key of the test issue to remove permanently (e.g., 'QA-999')")],
    ) -> Dict[str, Any]:
        """Permanently delete a Jira issue designated as a 'Test'."""
        log_usage("tool", "delete_test", {"issueKey": issue_key})
        username, password, token = extract_zephyr_auth(ctx)
        client = ZephyrClient(username=username, password=password, token=token)
        return await client.delete_test_case(issue_key)

    @mcp.tool()
    async def create_shared_test(
        ctx: Context,
        project_key: Annotated[str, Field(description="Jira project key")],
        summary: Annotated[str, Field(description="Test summary")],
        description: Annotated[Optional[str], Field(description="Description", default="")] = "",
    ) -> Dict[str, Any]:
        """Create a Test Case intended for shared use (with [SHARED] tag)."""
        log_usage("tool", "create_shared_test", {"projectKey": project_key})
        username, password, token = extract_zephyr_auth(ctx)
        client = ZephyrClient(username=username, password=password, token=token)
        tagged_summary = f"[SHARED] {summary}"
        return await client.create_test_case(project_key, tagged_summary, description)
