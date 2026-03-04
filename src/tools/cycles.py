from typing import Any, Dict, List, Annotated, Optional
from pydantic import Field
from src.client.zephyr_client import ZephyrClient
from src.middleware.rate_limit import RateLimiter
from src.middleware.auth import get_auth_from_headers
from src.utils.logging_utils import log_access

def register_cycle_tools(mcp, limiter: RateLimiter):
    
    def get_client(ctx):
        headers = ctx.request.headers if ctx and hasattr(ctx, 'request') else {}
        username, password, token = get_auth_from_headers(headers)
        return ZephyrClient(username=username, password=password, token=token), (token or username or "anonymous"), headers

    @mcp.tool()
    async def create_cycle(
        ctx: Any,
        name: Annotated[str, Field(description="The name of the test cycle to create (e.g., 'Sprint 45 Regression')")],
        project_id: Annotated[int, Field(description="The unique Jira project ID (e.g., 50493)")],
        version_id: Annotated[int, Field(description="The Jira version/release ID")],
        cloned_cycle_id: Annotated[Optional[str], Field(description="Optional: ID of an existing cycle to clone from", default="")],
        build: Annotated[Optional[str], Field(description="Optional: Build version code", default="")],
        environment: Annotated[Optional[str], Field(description="The environment name", default="QA")] = "QA",
        description: Annotated[Optional[str], Field(description="Detailed purpose of this cycle", default="")] = "",
        start_date: Annotated[Optional[str], Field(description="Cycle start date (e.g. '04/Mar/26')", default="")] = "",
        end_date: Annotated[Optional[str], Field(description="Cycle end date (e.g. '10/Mar/26')", default="")] = "",
    ) -> Dict[str, Any]:
        """Create or clone a Test Cycle in Zephyr with comprehensive details.
        
        This tool initiates a release milestone for grouping test executions.
        Rate limiting applies per user token or basic auth credentials.
        """
        client, user_id, headers = get_client(ctx)
        if not limiter.is_allowed(user_id):
            raise Exception("Rate limit exceeded for Zephyr MCP. Please adhere to the configured window limits.")

        log_access(user_id, "create_cycle", {"name": name, "projectId": project_id})
        return await client.create_test_cycle(
            name, project_id, version_id, cloned_cycle_id, 
            build, environment, description, start_date, end_date
        )

    @mcp.tool()
    async def fetch_cycles_from_version(
        ctx: Any,
        project_id: Annotated[int, Field(description="The numeric Jira project ID (e.g. 10123)")],
        version_id: Annotated[int, Field(description="The numeric Jira version/fixVersion ID (e.g. 45678)")],
    ) -> List[Dict[str, Any]]:
        """Retrieve all test cycles linked to a specific project and release version.
        
        Use this to discover which cycles exist for a given release so you can query their executions.
        Output: A list of JSON objects containing cycle names, IDs, and metadata.
        """
        client, user_id, headers = get_client(ctx)
        if not limiter.is_allowed(user_id):
            raise Exception("Rate limit exceeded for Zephyr MCP. Please wait approximately 10 seconds before fetching cycles again.")

        log_access(user_id, "fetch_cycles_from_version", {"projectId": project_id, "versionId": version_id})
        return await client.get_cycles(project_id, version_id)

    @mcp.tool()
    async def fetch_test_cases_from_cycle_with_stats(
        ctx: Any,
        cycle_id: Annotated[int, Field(description="The ID of the cycle to analyze")],
        project_id: Annotated[int, Field(description="The project ID")],
    ) -> Dict[str, Any]:
        """Fetch execution details for a cycle and calculate Pass/Fail statistics.
        
        Returns a summary including the list of executions and the count of different statuses.
        """
        client, user_id, headers = get_client(ctx)
        if not limiter.is_allowed(user_id):
            raise Exception("Rate limit exceeded.")

        log_access(user_id, "fetch_test_cases_from_cycle_with_stats", {"cycleId": cycle_id})
        executions = await client.get_executions_by_cycle(cycle_id, project_id)
        
        # Calculate stats
        # Status codes: 1: PASS, 2: FAIL, 3: WIP, 4: BLOCKED, -1: UNEXECUTED
        stats = {"PASS": 0, "FAIL": 0, "WIP": 0, "BLOCKED": 0, "UNEXECUTED": 0}
        for exe in executions.get("executions", []):
            status = exe.get("executionStatus", "-1")
            if status == "1": stats["PASS"] += 1
            elif status == "2": stats["FAIL"] += 1
            elif status == "3": stats["WIP"] += 1
            elif status == "4": stats["BLOCKED"] += 1
            else: stats["UNEXECUTED"] += 1
            
        return {
            "cycleId": cycle_id,
            "totalExecutions": len(executions.get("executions", [])),
            "statistics": stats,
            "executions": executions.get("executions", [])
        }

    @mcp.tool()
    async def get_issue_statuses(
        ctx: Any,
        project_id: Annotated[int, Field(description="The Jira project ID")],
    ) -> Dict[str, Any]:
        """Fetch high-level issue status metrics for a project."""
        client, user_id, headers = get_client(ctx)
        if not limiter.is_allowed(user_id):
            raise Exception("Rate limit exceeded.")
        
        log_access(user_id, "get_issue_statuses", {"projectId": project_id})
        return await client.get_issue_statuses(project_id)

    @mcp.tool()
    async def list_qa_projects(ctx: Any) -> List[Dict[str, Any]]:
        """List all discoverable Jira projects for QA integration."""
        client, user_id, headers = get_client(ctx)
        if not limiter.is_allowed(user_id):
            raise Exception("Rate limit exceeded.")

        log_access(user_id, "list_qa_projects", {})
        return await client.get_projects()

    @mcp.tool()
    async def add_folder(
        ctx: Any,
        name: Annotated[str, Field(description="The name of the folder to create")],
        parent_cycle_id: Annotated[int, Field(description="The ID of the parent cycle")],
        project_id: Annotated[int, Field(description="The Jira project ID")],
        version_id: Annotated[int, Field(description="The Jira version ID")],
    ) -> Dict[str, Any]:
        """Create a logical folder within a test cycle for better organization.
        
        Folders allow further grouping of test executions within a single release cycle.
        """
        client, user_id, headers = get_client(ctx)
        if not limiter.is_allowed(user_id):
            raise Exception("Rate limit exceeded.")

        log_access(user_id, "add_folder", {"name": name, "cycleId": parent_cycle_id})
        return await client.add_folder(name, parent_cycle_id, project_id, version_id)

    @mcp.tool()
    async def edit_cycle(
        ctx: Any,
        cycle_id: Annotated[int, Field(description="The numeric ID of the cycle to update")],
        name: Annotated[Optional[str], Field(description="New name for the cycle", default=None)] = None,
        build: Annotated[Optional[str], Field(description="New build version", default=None)] = None,
        environment: Annotated[Optional[str], Field(description="New environment name", default=None)] = None,
        description: Annotated[Optional[str], Field(description="New description", default=None)] = None,
    ) -> Dict[str, Any]:
        """Modify attributes of an existing test cycle.
        
        Provide only the fields you wish to change.
        """
        client, user_id, headers = get_client(ctx)
        if not limiter.is_allowed(user_id):
            raise Exception("Rate limit exceeded.")

        data = {}
        if name: data["name"] = name
        if build: data["build"] = build
        if environment: data["environment"] = environment
        if description: data["description"] = description

        log_access(user_id, "edit_cycle", {"cycleId": cycle_id})
        return await client.update_cycle(cycle_id, data)

    @mcp.tool()
    async def delete_cycle(
        ctx: Any,
        cycle_id: Annotated[int, Field(description="The numeric ID of the cycle to permanently delete")],
    ) -> Dict[str, Any]:
        """Permanently remove a test cycle and all its execution associations.
        
        Use with caution, as this action cannot be undone.
        """
        client, user_id, headers = get_client(ctx)
        if not limiter.is_allowed(user_id):
            raise Exception("Rate limit exceeded.")

        log_access(user_id, "delete_cycle", {"cycleId": cycle_id})
        return await client.delete_cycle(cycle_id)

    @mcp.tool()
    async def clone_cycle(
        ctx: Any,
        name: Annotated[str, Field(description="Name for the new cloned cycle")],
        project_id: Annotated[int, Field(description="Project ID")],
        version_id: Annotated[int, Field(description="Version ID")],
        cloned_cycle_id: Annotated[str, Field(description="ID of the cycle to clone from")],
        build: Annotated[Optional[str], Field(description="Build version", default="")] = "",
        environment: Annotated[Optional[str], Field(description="Environment", default="QA")] = "QA",
        description: Annotated[Optional[str], Field(description="Description", default="")] = "",
    ) -> Dict[str, Any]:
        """Create a copy of an existing cycle including its tests and groupings.
        
        Highly efficient for repeating regression suites across different builds.
        """
        client, user_id, headers = get_client(ctx)
        if not limiter.is_allowed(user_id):
            raise Exception("Rate limit exceeded.")

        log_access(user_id, "clone_cycle", {"clonedFrom": cloned_cycle_id, "newName": name})
        return await client.clone_cycle(name, project_id, version_id, cloned_cycle_id, build, environment, description)
