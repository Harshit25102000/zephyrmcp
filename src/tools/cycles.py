from typing import Any, Dict, List, Annotated, Optional
from mcp.server.fastmcp import Context
from pydantic import Field
from src.utils.logging_utils import log_usage
from src.middleware.auth import extract_zephyr_auth
from src.client.zephyr_client import ZephyrClient

def register_cycle_tools(mcp, limiter=None):
    
    # ============================================================
    # RESOURCES (Read Operations)
    # ============================================================

    @mcp.resource("zephyr://version/{project_id}/{version_id}/cycles")
    async def fetch_cycles_from_version(project_id: int, version_id: int, ctx: Context) -> str:
        """Retrieve all test cycles linked to a specific project and release version."""
        log_usage("resource", "fetch_cycles_from_version", {"projectId": project_id, "versionId": version_id})
        username, password, token = extract_zephyr_auth(ctx)
        client = ZephyrClient(username=username, password=password, token=token)
        cycles = await client.get_cycles(project_id, version_id)
        
        output = [f"Cycles for Project {project_id}, Version {version_id}:"]
        for c in cycles:
            output.append(f"- {c.get('name')} (ID: {c.get('id')}) | Status: {c.get('status')}")
        return "\n".join(output)

    @mcp.resource("zephyr://cycle/{cycle_id}/project/{project_id}/stats")
    async def fetch_cycle_stats(cycle_id: int, project_id: int, ctx: Context) -> str:
        """Fetch execution details for a cycle and calculate Pass/Fail statistics."""
        log_usage("resource", "fetch_cycle_stats", {"cycleId": cycle_id})
        username, password, token = extract_zephyr_auth(ctx)
        client = ZephyrClient(username=username, password=password, token=token)
        executions = await client.get_executions_by_cycle(cycle_id, project_id)
        
        stats = {"PASS": 0, "FAIL": 0, "WIP": 0, "BLOCKED": 0, "UNEXECUTED": 0}
        for exe in executions.get("executions", []):
            status = exe.get("executionStatus", "-1")
            if status == "1": stats["PASS"] += 1
            elif status == "2": stats["FAIL"] += 1
            elif status == "3": stats["WIP"] += 1
            elif status == "4": stats["BLOCKED"] += 1
            else: stats["UNEXECUTED"] += 1
            
        return f"Cycle {cycle_id} Stats:\n" + "\n".join([f"{k}: {v}" for k, v in stats.items()])

    @mcp.resource("zephyr://project/{project_id}/statuses")
    async def get_issue_statuses(project_id: int, ctx: Context) -> str:
        """Fetch high-level issue status metrics for a project."""
        log_usage("resource", "get_issue_statuses", {"projectId": project_id})
        username, password, token = extract_zephyr_auth(ctx)
        client = ZephyrClient(username=username, password=password, token=token)
        statuses = await client.get_issue_statuses(project_id)
        return str(statuses)

    @mcp.resource("zephyr://system/projects")
    async def list_qa_projects(ctx: Context) -> str:
        """List all discoverable Jira projects for QA integration."""
        log_usage("resource", "list_qa_projects", {})
        username, password, token = extract_zephyr_auth(ctx)
        client = ZephyrClient(username=username, password=password, token=token)
        projects = await client.get_projects()
        
        output = ["Available Projects:"]
        for p in projects:
            output.append(f"- {p.get('name')} (ID: {p.get('id')}, Key: {p.get('key')})")
        return "\n".join(output)

    # ============================================================
    # TOOLS (Write Operations)
    # ============================================================

    @mcp.tool()
    async def create_cycle(
        ctx: Context,
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
        """Create or clone a Test Cycle in Zephyr."""
        log_usage("tool", "create_cycle", {"name": name, "projectId": project_id})
        username, password, token = extract_zephyr_auth(ctx)
        client = ZephyrClient(username=username, password=password, token=token)
        return await client.create_test_cycle(
            name, project_id, version_id, cloned_cycle_id, 
            build, environment, description, start_date, end_date
        )

    @mcp.tool()
    async def add_folder(
        ctx: Context,
        name: Annotated[str, Field(description="The name of the folder to create")],
        parent_cycle_id: Annotated[int, Field(description="The ID of the parent cycle")],
        project_id: Annotated[int, Field(description="The Jira project ID")],
        version_id: Annotated[int, Field(description="The Jira version ID")],
    ) -> Dict[str, Any]:
        """Create a logical folder within a test cycle."""
        log_usage("tool", "add_folder", {"name": name, "cycleId": parent_cycle_id})
        username, password, token = extract_zephyr_auth(ctx)
        client = ZephyrClient(username=username, password=password, token=token)
        return await client.add_folder(name, parent_cycle_id, project_id, version_id)

    @mcp.tool()
    async def edit_cycle(
        ctx: Context,
        cycle_id: Annotated[int, Field(description="The numeric ID of the cycle to update")],
        name: Annotated[Optional[str], Field(description="New name for the cycle", default=None)] = None,
        build: Annotated[Optional[str], Field(description="New build version", default=None)] = None,
        environment: Annotated[Optional[str], Field(description="New environment name", default=None)] = None,
        description: Annotated[Optional[str], Field(description="New description", default=None)] = None,
    ) -> Dict[str, Any]:
        """Modify attributes of an existing test cycle."""
        log_usage("tool", "edit_cycle", {"cycleId": cycle_id})
        username, password, token = extract_zephyr_auth(ctx)
        client = ZephyrClient(username=username, password=password, token=token)
        data = {}
        if name: data["name"] = name
        if build: data["build"] = build
        if environment: data["environment"] = environment
        if description: data["description"] = description
        return await client.update_cycle(cycle_id, data)

    @mcp.tool()
    async def delete_cycle(
        ctx: Context,
        cycle_id: Annotated[int, Field(description="The numeric ID of the cycle to permanently delete")],
    ) -> Dict[str, Any]:
        """Permanently remove a test cycle."""
        log_usage("tool", "delete_cycle", {"cycleId": cycle_id})
        username, password, token = extract_zephyr_auth(ctx)
        client = ZephyrClient(username=username, password=password, token=token)
        return await client.delete_cycle(cycle_id)

    @mcp.tool()
    async def clone_cycle(
        ctx: Context,
        name: Annotated[str, Field(description="Name for the new cloned cycle")],
        project_id: Annotated[int, Field(description="Project ID")],
        version_id: Annotated[int, Field(description="Version ID")],
        cloned_cycle_id: Annotated[str, Field(description="ID of the cycle to clone from")],
        build: Annotated[Optional[str], Field(description="Build version", default="")] = "",
        environment: Annotated[Optional[str], Field(description="Environment", default="QA")] = "QA",
        description: Annotated[Optional[str], Field(description="Description", default="")] = "",
    ) -> Dict[str, Any]:
        """Create a copy of an existing cycle."""
        log_usage("tool", "clone_cycle", {"clonedFrom": cloned_cycle_id})
        username, password, token = extract_zephyr_auth(ctx)
        client = ZephyrClient(username=username, password=password, token=token)
        return await client.clone_cycle(name, project_id, version_id, cloned_cycle_id, build, environment, description)
