from typing import Any, Dict, List, Optional
from fastmcp import FastMCP
from fastmcp.server.context import Context


def register_cycle_tools(mcp, JIRA_API_URL, ZAPI_BASE_URL, log_usage, extract_zephyr_auth, check_rate_limit, zephyr_request, filter_fields, check_tool_limit, TOOL_MAX_ITEMS, BULK_MAX_ITEMS, MAX_RESULTS):
    """Register all test cycle management tools and resources."""

    # ============================================================
    # RESOURCES â€” read-only
    # ============================================================

    @mcp.resource("zephyr://system/projects")
    async def list_projects(ctx: Context) -> str:
        """
        [RESOURCE] List all Jira projects available to the authenticated user.

        URI: zephyr://system/projects
        No parameters required.

        Returns a formatted list of projects with ID, key, and name.
        Use this first to find the project_id and project_key needed by other tools.
        Rate-limited: use this once and cache results rather than calling repeatedly.
        """
        check_rate_limit(ctx)
        log_usage("resource", "list_projects", {})
        username, password, token = extract_zephyr_auth(ctx)
        projects = await zephyr_request("GET", f"{JIRA_API_URL}/project", username, password, token)
        lines = ["Available Jira Projects:"]
        for p in projects:
            lines.append(f"- ID: {p['id']} | Key: {p['key']} | Name: {p['name']}")
        return "\n".join(lines)

    @mcp.resource("zephyr://version/{project_id}/{version_id}/cycles")
    async def list_cycles(project_id: str, version_id: str, ctx: Context) -> str:
        """
        [RESOURCE] List all test cycles for a specific project and version.

        URI: zephyr://version/{project_id}/{version_id}/cycles
        - project_id: Numeric Jira project ID (from zephyr://system/projects)
        - version_id: Numeric Jira version ID (use -1 for unscheduled)

        Returns a formatted list of cycles with their IDs, names, and status.
        Use the cycle id values returned here when calling create tools.
        """
        check_rate_limit(ctx)
        log_usage("resource", "list_cycles", {"projectId": project_id, "versionId": version_id})
        username, password, token = extract_zephyr_auth(ctx)

        result = await zephyr_request(
            "GET", f"{ZAPI_BASE_URL}/cycle",
            username, password, token,
            params={"projectId": project_id, "versionId": version_id}
        )
        lines = [f"Cycles for Project {project_id}, Version {version_id}:"]
        for key, val in result.items():
            if key != "recordsCount" and isinstance(val, dict):
                lines.append(f"- ID: {key} | Name: {val.get('name')} | Build: {val.get('build','')} | Env: {val.get('environment','')}")
        return "\n".join(lines)

    # ============================================================
    # TOOLS â€” write/read operations
    # ============================================================

    @mcp.tool()
    async def get_projects(
        ctx: Context,
        fields: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        List all Jira projects available to the authenticated user (as structured data).

        Use this when you need machine-readable project data.
        For a human-readable summary, use the zephyr://system/projects resource instead.

        Input:
        - fields (optional): List of project keys to include per item.
          Available keys: id, key, name, description, projectTypeKey, lead, url, avatarUrls
          Example: ["id", "key", "name"]

        Output: List of project objects (filtered if fields specified).

        Errors:
        - 401/403: Authentication or permission failure.
        """
        check_rate_limit(ctx)
        log_usage("tool", "get_projects", {"fields": fields})
        username, password, token = extract_zephyr_auth(ctx)
        projects = await zephyr_request("GET", f"{JIRA_API_URL}/project", username, password, token, params={"maxResults": MAX_RESULTS})
        result = [{"id": p["id"], "key": p["key"], "name": p["name"], **{k: p.get(k) for k in (fields or []) if k not in ("id", "key", "name")}} for p in projects[:MAX_RESULTS]]
        return filter_fields(result, fields) if fields else result

    @mcp.tool()
    async def get_cycles(
        ctx: Context,
        project_id: int,
        version_id: int,
        fields: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all test cycles for a specific project and release version (as structured data).

        Use this to find cycle IDs needed for creating/editing executions.
        For a human-readable summary, use zephyr://version/{project_id}/{version_id}/cycles resource.

        Input:
        - project_id (required): Numeric Jira project ID. Use get_projects to find.
        - version_id (required): Numeric Jira version/fixVersion ID. Use -1 for unscheduled.
        - fields (optional): List of cycle keys to return per cycle.
          Available keys: id, name, description, build, environment, startDate, endDate, totalExecutions
          Example: ["id", "name", "build"] â€” returns only those three fields per cycle.

        Output: List of cycle objects (filtered if fields specified).

        Errors:
        - 404: Project or version not found.
        """
        check_rate_limit(ctx)
        log_usage("tool", "get_cycles", {"projectId": project_id, "versionId": version_id, "fields": fields})
        username, password, token = extract_zephyr_auth(ctx)

        result = await zephyr_request(
            "GET", f"{ZAPI_BASE_URL}/cycle",
            username, password, token,
            params={"projectId": project_id, "versionId": version_id}
        )
        cycles = []
        for key, val in result.items():
            if key != "recordsCount" and isinstance(val, dict):
                val["id"] = key
                cycles.append(val)
        # Cap results to TOOL_MAX_ITEMS
        cycles = cycles[:TOOL_MAX_ITEMS]
        return filter_fields(cycles, fields)

    @mcp.tool()
    async def fetch_cycle_stats(
        ctx: Context,
        cycle_id: int,
        project_id: int,
        fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Fetch test execution statistics for a cycle: Pass/Fail/WIP/Blocked/Unexecuted counts.

        Use this for a cycle-level release summary or to identify failing areas.

        Input:
        - cycle_id (required): Numeric Zephyr cycle ID. Use get_cycles to find.
        - project_id (required): Numeric Jira project ID.
        - fields (optional): List of keys to include in response.
          Available keys: cycleId, totalExecutions, statistics
          Example: ["statistics"] â€” returns only the stats breakdown.

        Output: { cycleId, totalExecutions, statistics: { PASS, FAIL, WIP, BLOCKED, UNEXECUTED } }

        Errors:
        - 404: Cycle not found for the given project.
        """
        check_rate_limit(ctx)
        log_usage("tool", "fetch_cycle_stats", {"cycleId": cycle_id, "projectId": project_id})
        username, password, token = extract_zephyr_auth(ctx)

        result = await zephyr_request(
            "GET", f"{ZAPI_BASE_URL}/execution",
            username, password, token,
            params={"cycleId": cycle_id, "projectId": project_id}
        )

        stats = {"PASS": 0, "FAIL": 0, "WIP": 0, "BLOCKED": 0, "UNEXECUTED": 0}
        for exe in result.get("executions", []):
            status = str(exe.get("executionStatus", "-1"))
            if status == "1": stats["PASS"] += 1
            elif status == "2": stats["FAIL"] += 1
            elif status == "3": stats["WIP"] += 1
            elif status == "4": stats["BLOCKED"] += 1
            else: stats["UNEXECUTED"] += 1

        response = {"cycleId": cycle_id, "totalExecutions": sum(stats.values()), "statistics": stats}
        return filter_fields(response, fields)

    @mcp.tool()
    async def get_issue_statuses(
        ctx: Context,
        project_id: int,
        fields: Optional[List[str]] = None,
    ) -> Any:
        """
        Fetch the workflow status categories and transitions available for a Jira project.

        Use this to find valid transition_id values before calling update_jira_status.

        Input:
        - project_id (required): Numeric Jira project ID.
        - fields (optional): List of keys to include per status item.

        Output: Jira status category and issue type metadata.

        Errors:
        - 404: Project not found.
        """
        check_rate_limit(ctx)
        log_usage("tool", "get_issue_statuses", {"projectId": project_id})
        username, password, token = extract_zephyr_auth(ctx)
        result = await zephyr_request("GET", f"{JIRA_API_URL}/project/{project_id}/statuses", username, password, token)
        return filter_fields(result, fields)

    @mcp.tool()
    async def create_cycle(
        ctx: Context,
        name: str,
        project_id: int,
        version_id: int,
        cloned_cycle_id: str = "",
        build: str = "",
        environment: str = "QA",
        description: str = "",
        start_date: str = "",
        end_date: str = "",
        fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new Test Cycle in Zephyr for a specific project and version.

        Optionally clone an existing cycle structure by providing cloned_cycle_id.
        After creation, assign tests using add_test_cases_to_cycle.

        Input:
        - name (required): Descriptive cycle name (e.g. 'Sprint 45 Regression').
        - project_id (required): Numeric Jira project ID. Use get_projects to find.
        - version_id (required): Numeric Jira version ID. Use -1 for unscheduled.
        - cloned_cycle_id (optional): ID of an existing cycle to clone structure from.
        - build (optional): Build/release version identifier (e.g. '2.5.1').
        - environment (optional): Target environment (default: 'QA').
        - description (optional): Purpose and scope of this cycle.
        - start_date (optional): Format as 'DD/Mon/YY' (e.g. '03/Mar/26').
        - end_date (optional): Format as 'DD/Mon/YY'.
        - fields (optional): List of response keys to include (e.g. ["id", "name"]).

        Output: Created cycle object (filtered if fields specified).

        Errors:
        - 400: Invalid project_id, version_id, or date format.
        """
        check_rate_limit(ctx)
        log_usage("tool", "create_cycle", {"name": name, "projectId": project_id})
        username, password, token = extract_zephyr_auth(ctx)

        payload = {
            "name": name, "projectId": project_id, "versionId": version_id,
            "build": build, "environment": environment, "description": description,
        }
        if start_date: payload["startDate"] = start_date
        if end_date: payload["endDate"] = end_date
        if cloned_cycle_id: payload["clonedCycleId"] = cloned_cycle_id

        result = await zephyr_request("POST", f"{ZAPI_BASE_URL}/cycle", username, password, token, json_data=payload)
        return filter_fields(result, fields)

    @mcp.tool()
    async def clone_cycle(
        ctx: Context,
        name: str,
        project_id: int,
        version_id: int,
        cloned_cycle_id: str,
        build: str = "",
        environment: str = "QA",
        description: str = "",
        fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a full copy of an existing test cycle, including all linked tests.

        Use this to set up regression cycles by cloning functional cycles.

        Input:
        - name (required): Name for the new cloned cycle.
        - project_id (required): Numeric Jira project ID.
        - version_id (required): Numeric Jira version ID.
        - cloned_cycle_id (required): ID of the source cycle to clone from.
        - build, environment, description (optional): Override these from the source.
        - fields (optional): List of response keys to include.

        Output: Created cycle object from Zephyr (filtered if fields specified).
        """
        check_rate_limit(ctx)
        log_usage("tool", "clone_cycle", {"clonedFrom": cloned_cycle_id, "newName": name})
        username, password, token = extract_zephyr_auth(ctx)

        payload = {
            "name": name, "projectId": project_id, "versionId": version_id,
            "clonedCycleId": cloned_cycle_id, "build": build,
            "environment": environment, "description": description,
        }
        result = await zephyr_request("POST", f"{ZAPI_BASE_URL}/cycle", username, password, token, json_data=payload)
        return filter_fields(result, fields)

    @mcp.tool()
    async def edit_cycle(
        ctx: Context,
        cycle_id: int,
        name: Optional[str] = None,
        build: Optional[str] = None,
        environment: Optional[str] = None,
        description: Optional[str] = None,
        fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Update metadata of an existing test cycle. Only provided fields are updated.

        Does NOT affect linked tests or execution statuses.

        Input:
        - cycle_id (required): Numeric Zephyr cycle ID.
        - name, build, environment, description (optional): Fields to update.
        - fields (optional): List of response keys to return (e.g. ["id", "name"]).

        Output: Updated cycle object (filtered if fields specified).

        Errors:
        - 404: Cycle not found.
        """
        check_rate_limit(ctx)
        log_usage("tool", "edit_cycle", {"cycleId": cycle_id})
        username, password, token = extract_zephyr_auth(ctx)

        payload = {"id": cycle_id}
        if name is not None: payload["name"] = name
        if build is not None: payload["build"] = build
        if environment is not None: payload["environment"] = environment
        if description is not None: payload["description"] = description

        result = await zephyr_request("PUT", f"{ZAPI_BASE_URL}/cycle/{cycle_id}", username, password, token, json_data=payload)
        return filter_fields(result, fields)

    @mcp.tool()
    async def delete_cycle(
        ctx: Context,
        cycle_id: int,
    ) -> Dict[str, Any]:
        """
        Permanently delete a test cycle and all its associated execution records.

        WARNING: This is irreversible. All execution history for this cycle will be lost.

        Input:
        - cycle_id (required): Numeric Zephyr cycle ID to delete.

        Output: { status: "deleted", cycle_id }

        Errors:
        - 403: Insufficient permissions to delete this cycle.
        - 404: Cycle not found.
        """
        check_rate_limit(ctx)
        log_usage("tool", "delete_cycle", {"cycleId": cycle_id})
        username, password, token = extract_zephyr_auth(ctx)
        await zephyr_request("DELETE", f"{ZAPI_BASE_URL}/cycle/{cycle_id}", username, password, token)
        return {"status": "deleted", "cycle_id": cycle_id}

    @mcp.tool()
    async def add_folder(
        ctx: Context,
        name: str,
        parent_cycle_id: int,
        project_id: int,
        version_id: int,
        fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a logical folder inside a test cycle to organize test groups.

        Input:
        - name (required): Folder display name (e.g. 'Login Tests', 'Smoke Suite').
        - parent_cycle_id (required): Numeric ID of the parent cycle.
        - project_id (required): Numeric Jira project ID.
        - version_id (required): Numeric Jira version ID.
        - fields (optional): List of response keys to include.

        Output: Created folder object from Zephyr (filtered if fields specified).
        """
        check_rate_limit(ctx)
        log_usage("tool", "add_folder", {"name": name, "cycleId": parent_cycle_id})
        username, password, token = extract_zephyr_auth(ctx)

        payload = {"name": name, "cycleId": parent_cycle_id, "projectId": project_id, "versionId": version_id}
        result = await zephyr_request("POST", f"{ZAPI_BASE_URL}/folder/create", username, password, token, json_data=payload)
        return filter_fields(result, fields)
