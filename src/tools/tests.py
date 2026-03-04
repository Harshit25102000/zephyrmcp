from typing import Any, Dict, List, Optional
from fastmcp import FastMCP
from fastmcp.server.context import Context


def register_test_tools(mcp, JIRA_API_URL, ZAPI_BASE_URL, log_usage, extract_zephyr_auth, check_rate_limit, zephyr_request, zephyr_upload, filter_fields, check_tool_limit, TOOL_MAX_ITEMS, BULK_MAX_ITEMS, MAX_RESULTS):
    """Register all test case management tools and resources."""

    # ============================================================
    # RESOURCES â€” read-only, no state change
    # ============================================================

    @mcp.resource("zephyr://project/{project_key}/tests")
    async def list_project_tests(project_key: str, ctx: Context) -> str:
        """
        [RESOURCE] List all test issues in a given Jira project.

        URI: zephyr://project/{project_key}/tests
        - project_key: Jira project key (e.g. 'QA', 'AUTO')

        Returns a formatted list of test issues with their key and summary.
        Use this to discover existing tests before creating duplicates.
        """
        check_rate_limit(ctx)
        log_usage("resource", "list_project_tests", {"projectKey": project_key})
        username, password, token = extract_zephyr_auth(ctx)

        result = await zephyr_request(
            "GET", f"{JIRA_API_URL}/search",
            username, password, token,
            params={"jql": f"project={project_key} AND issuetype=Test", "fields": "summary,status", "maxResults": MAX_RESULTS}
        )
        issues = result.get("issues", [])
        lines = [f"Tests in project {project_key} ({len(issues)} found):"]
        for i in issues:
            lines.append(f"- {i['key']}: {i['fields']['summary']}")
        return "\n".join(lines)

    @mcp.resource("zephyr://test/{issue_id}/steps")
    async def get_test_steps_resource(issue_id: str, ctx: Context) -> str:
        """
        [RESOURCE] Fetch all steps defined for a Zephyr test case.

        URI: zephyr://test/{issue_id}/steps
        - issue_id: Numeric Jira issue ID (NOT the key like QA-123, use the number)

        Returns a formatted list of test steps with order, action, test data, and expected result.
        Use this to inspect a test before editing its steps.
        """
        check_rate_limit(ctx)
        log_usage("resource", "get_test_steps", {"issueId": issue_id})
        username, password, token = extract_zephyr_auth(ctx)

        steps = await zephyr_request("GET", f"{ZAPI_BASE_URL}/teststep/{issue_id}", username, password, token)
        if not steps:
            return f"No steps found for test issue ID {issue_id}."

        lines = [f"Steps for test (Issue ID: {issue_id}):"]
        for s in (steps if isinstance(steps, list) else steps.get("stepBeanCollection", [])):
            lines.append(f"\nStep {s.get('orderId')}:")
            lines.append(f"  Action : {s.get('step', '')}")
            lines.append(f"  Data   : {s.get('data', '')}")
            lines.append(f"  Result : {s.get('result', '')}")
        return "\n".join(lines)

    # ============================================================
    # TOOLS â€” write operations
    # ============================================================

    @mcp.tool()
    async def create_test_case(
        ctx: Context,
        project_key: str,
        summary: str,
        description: str = "",
        fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new Jira issue of type 'Test' in the specified project.

        Use this when a new test scenario needs to be tracked in Zephyr.
        After creating, use insert_test_step to add steps, then add_test_cases_to_cycle to assign to a cycle.

        Input:
        - project_key (required): Jira project key (e.g. 'QA'). Use get_projects to find valid keys.
        - summary (required): Short, descriptive title for the test case.
        - description (optional): Detailed test description including prerequisites or scope.
        - fields (optional): List of keys to include in response (e.g. ["id", "key"]).
          If omitted, full response is returned.

        Output: { id, key, self } â€” use 'id' (numeric) for step operations, 'key' for status updates.

        Errors:
        - 400: Invalid project_key or missing required fields.
        - 403: Your token lacks permission to create issues in this project.
        """
        check_rate_limit(ctx)
        log_usage("tool", "create_test_case", {"projectKey": project_key, "summary": summary})
        username, password, token = extract_zephyr_auth(ctx)

        payload = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "description": description,
                "issuetype": {"name": "Test"},
            }
        }
        result = await zephyr_request("POST", f"{JIRA_API_URL}/issue", username, password, token, json_data=payload)
        response = {"id": result.get("id"), "key": result.get("key"), "self": result.get("self")}
        return filter_fields(response, fields)

    @mcp.tool()
    async def create_shared_test(
        ctx: Context,
        project_key: str,
        summary: str,
        description: str = "",
        fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a shared/reusable Test Case (automatically prefixed with [SHARED]).

        Use this for tests intended to be linked from multiple cycles or regression suites.
        Shared tests are identified by the [SHARED] prefix in their summary.

        Input:
        - project_key (required): Jira project key.
        - summary (required): Test summary â€” [SHARED] prefix is applied automatically.
        - description (optional): Detailed description.
        - fields (optional): List of response keys to include (e.g. ["id", "key"]).

        Output: { id, key, self }
        """
        check_rate_limit(ctx)
        log_usage("tool", "create_shared_test", {"projectKey": project_key})
        username, password, token = extract_zephyr_auth(ctx)

        payload = {
            "fields": {
                "project": {"key": project_key},
                "summary": f"[SHARED] {summary}",
                "description": description,
                "issuetype": {"name": "Test"},
            }
        }
        result = await zephyr_request("POST", f"{JIRA_API_URL}/issue", username, password, token, json_data=payload)
        response = {"id": result.get("id"), "key": result.get("key"), "self": result.get("self")}
        return filter_fields(response, fields)

    @mcp.tool()
    async def delete_test(
        ctx: Context,
        issue_key: str,
    ) -> Dict[str, Any]:
        """
        Permanently delete a Jira issue of type 'Test'. This action is irreversible.

        WARNING: This deletes the issue from Jira entirely, removing it from all linked cycles.
        Only use when a test is truly obsolete.

        Input:
        - issue_key (required): Jira issue key (e.g. 'QA-123').

        Output: { status: "deleted", issue_key }

        Errors:
        - 404: Issue not found. Verify the issue_key.
        - 403: Insufficient permissions to delete this issue.
        """
        check_rate_limit(ctx)
        log_usage("tool", "delete_test", {"issueKey": issue_key})
        username, password, token = extract_zephyr_auth(ctx)
        await zephyr_request("DELETE", f"{JIRA_API_URL}/issue/{issue_key}", username, password, token)
        return {"status": "deleted", "issue_key": issue_key}

    @mcp.tool()
    async def update_jira_status(
        ctx: Context,
        issue_key: str,
        transition_id: int,
    ) -> Dict[str, Any]:
        """
        Transition a Jira issue to a new workflow status (e.g. In Progress, Done).

        Use this to update the overall status of a test issue in Jira's workflow.
        This is different from updating the *execution* result in Zephyr (use execute_test for that).

        Input:
        - issue_key (required): Jira issue key (e.g. 'QA-123').
        - transition_id (required): Numeric workflow transition ID.
          Common IDs: 11=To Do, 21=In Progress, 31=Done (these vary by project â€” fetch from Jira if unsure).

        Output: { status: "transitioned", issue_key, transition_id }

        Errors:
        - 400: Invalid transition ID for the current issue state.
        - 404: Issue not found.
        """
        check_rate_limit(ctx)
        log_usage("tool", "update_jira_status", {"issueKey": issue_key, "transitionId": transition_id})
        username, password, token = extract_zephyr_auth(ctx)
        await zephyr_request("POST", f"{JIRA_API_URL}/issue/{issue_key}/transitions", username, password, token, json_data={"transition": {"id": transition_id}})
        return {"status": "transitioned", "issue_key": issue_key, "transition_id": transition_id}

    @mcp.tool()
    async def add_test_cases_to_cycle(
        ctx: Context,
        cycle_id: str,
        project_id: int,
        version_id: int,
        issue_ids: List[int],
        fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Bulk assign multiple existing test cases to a specific test cycle.

        Use this instead of individual assignments to minimize API calls (rate limit friendly).
        All listed issues will be added as executions in the target cycle.

        Input:
        - cycle_id (required): Zephyr cycle ID as string (e.g. '102'). Use get_cycles to find.
        - project_id (required): Numeric Jira project ID. Use get_projects to find.
        - version_id (required): Numeric Jira version ID. Use -1 for unscheduled.
        - issue_ids (required): List of numeric Jira issue IDs to add. NOT issue keys.
          **Limit**: maximum {BULK_MAX_ITEMS} issue IDs per call. Split larger sets into batches.
        - fields (optional): List of response keys to include.

        Output: Confirmation from Zephyr with job status.

        Errors:
        - 400: Invalid cycle_id, project_id or version_id.
        - 404: Cycle or issues not found.
        - Tool limit: Exceeding {BULK_MAX_ITEMS} issue_ids in one call will be rejected.
        """
        check_rate_limit(ctx)
        check_tool_limit(issue_ids, "issue_ids", limit=BULK_MAX_ITEMS)
        log_usage("tool", "add_test_cases_to_cycle", {"cycleId": cycle_id, "count": len(issue_ids)})
        username, password, token = extract_zephyr_auth(ctx)

        payload = {
            "issues": issue_ids,
            "versionId": version_id,
            "cycleId": cycle_id,
            "projectId": project_id,
            "method": "1",
        }
        result = await zephyr_request("POST", f"{ZAPI_BASE_URL}/execution/addTestsToCycle", username, password, token, json_data=payload)
        return filter_fields(result, fields)

    @mcp.tool()
    async def insert_test_step(
        ctx: Context,
        issue_id: str,
        step: str,
        order_id: int,
        data: str = "",
        result: str = "",
        fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Insert a new test step at a specific position in a Zephyr test case.

        Use this to build out the step-by-step procedure for a test after creating it.
        Steps are ordered by order_id (1-indexed). Inserting at an existing position shifts subsequent steps.

        Input:
        - issue_id (required): Numeric Jira issue ID (not key â€” use the number from create_test_case).
        - step (required): The action/instruction for this step (e.g. 'Click Login button').
        - order_id (required): Position in the step list (1 = first step).
        - data (optional): Test data or preconditions for this step.
        - result (optional): Expected outcome after performing this step.
        - fields (optional): List of response keys to include (e.g. ["id", "orderId"]).

        Output: Created step object from Zephyr.
        """
        check_rate_limit(ctx)
        log_usage("tool", "insert_test_step", {"issueId": issue_id, "order": order_id})
        username, password, token = extract_zephyr_auth(ctx)

        payload = {"step": step, "data": data, "result": result, "orderId": order_id}
        api_result = await zephyr_request("POST", f"{ZAPI_BASE_URL}/teststep/{issue_id}", username, password, token, json_data=payload)
        return filter_fields(api_result, fields)

    @mcp.tool()
    async def update_test_step(
        ctx: Context,
        issue_id: str,
        step_id: int,
        step: str,
        data: str = "",
        result: str = "",
        fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Update the content of an existing test step.

        Use this to modify the action, test data, or expected result of a step.
        Use zephyr://test/{issue_id}/steps resource first to get step_id values.

        Input:
        - issue_id (required): Numeric Jira issue ID.
        - step_id (required): Numeric Zephyr step ID (from the steps resource).
        - step (required): Updated action/instruction text.
        - data (optional): Updated test data.
        - result (optional): Updated expected result.
        - fields (optional): List of response keys to include.

        Output: Updated step object.
        """
        check_rate_limit(ctx)
        log_usage("tool", "update_test_step", {"issueId": issue_id, "stepId": step_id})
        username, password, token = extract_zephyr_auth(ctx)

        payload = {"step": step, "data": data, "result": result}
        api_result = await zephyr_request("PUT", f"{ZAPI_BASE_URL}/teststep/{issue_id}/{step_id}", username, password, token, json_data=payload)
        return filter_fields(api_result, fields)

    @mcp.tool()
    async def delete_test_step(
        ctx: Context,
        issue_id: str,
        step_id: int,
    ) -> Dict[str, Any]:
        """
        Delete a specific step from a test case. This action is irreversible.

        Use this to remove outdated or incorrect steps.
        Use zephyr://test/{issue_id}/steps to find the step_id before deleting.

        Input:
        - issue_id (required): Numeric Jira issue ID.
        - step_id (required): Numeric Zephyr step ID to remove.

        Output: { status: "deleted", step_id }

        Errors:
        - 404: Step ID not found for the given issue.
        """
        check_rate_limit(ctx)
        log_usage("tool", "delete_test_step", {"issueId": issue_id, "stepId": step_id})
        username, password, token = extract_zephyr_auth(ctx)
        await zephyr_request("DELETE", f"{ZAPI_BASE_URL}/teststep/{issue_id}/{step_id}", username, password, token)
        return {"status": "deleted", "step_id": step_id}

    @mcp.tool()
    async def get_test_steps(
        ctx: Context,
        issue_id: str,
        fields: Optional[List[str]] = None,
    ) -> Any:
        """
        Fetch all defined steps for a Zephyr test case (as structured data).

        Input:
        - issue_id (required): Numeric Jira issue ID (e.g. '10234').
        - fields (optional): List of step keys to include per step (e.g. ["orderId", "step", "result"]).
          Available keys: orderId, step, data, result, id, htmlStep, htmlData, htmlResult

        Output: List of step objects (optionally filtered to requested fields).
        """
        check_rate_limit(ctx)
        log_usage("tool", "get_test_steps", {"issueId": issue_id, "fields": fields})
        username, password, token = extract_zephyr_auth(ctx)
        result = await zephyr_request("GET", f"{ZAPI_BASE_URL}/teststep/{issue_id}", username, password, token)
        return filter_fields(result, fields)
