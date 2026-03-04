from typing import Optional, Dict, Any
from .base import ZephyrBaseClient

class ZephyrTestClient(ZephyrBaseClient):
    """
    Client mixin for Test Case & Step Management.
    """
    async def create_test_case(self, project_key: str, summary: str, description: str = ""):
        """
        Create a Jira issue of type 'Test'.
        Uses the standard Jira Issue API since Zephyr tests are Jira issues.
        """
        endpoint = "/rest/api/2/issue"
        data = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "description": description,
                "issuetype": {"name": "Test"}
            }
        }
        return await self._request("POST", endpoint, json_data=data)

    async def get_test_steps(self, issue_id: str):
        """Fetch test steps for a specific issue."""
        endpoint = f"/rest/zapi/latest/teststep/{issue_id}"
        return await self._request("GET", endpoint)

    async def add_test_step(self, issue_id: str, step: str, data: str = "", result: str = ""):
        """Add a new test step to an issue."""
        endpoint = f"/rest/zapi/latest/teststep/{issue_id}"
        payload = {"step": step, "data": data, "result": result}
        return await self._request("POST", endpoint, json_data=payload)

    async def add_test_cases_to_cycle(self, cycle_id: str, project_id: int, version_id: int, issue_ids: list):
        """
        Bulk add test cases to an existing cycle.
        """
        endpoint = "/rest/zapi/latest/execution/addTests"
        data = {
            "cycleId": cycle_id,
            "projectId": project_id,
            "versionId": version_id,
            "issues": issue_ids,
            "method": "1" # Method 1 means by issue IDs
        }
        return await self._request("POST", endpoint, json_data=data)

    async def update_jira_status(self, issue_key: str, transition_id: int):
        """
        Update the Jira status of a test (Jira issue transition).
        """
        endpoint = f"/rest/api/2/issue/{issue_key}/transitions"
        data = {"transition": {"id": transition_id}}
        return await self._request("POST", endpoint, json_data=data)

    async def insert_test_step(self, issue_id: str, step: str, order_id: int, data: str = "", result: str = ""):
        """Insert a step at a specific position."""
        endpoint = f"/rest/zapi/latest/teststep/{issue_id}"
        payload = {"step": step, "data": data, "result": result, "orderId": order_id}
        # In some ZAPI versions, POST with orderId handles insertion
        return await self._request("POST", endpoint, json_data=payload)

    async def update_test_step(self, issue_id: str, step_id: int, step: str, data: str = "", result: str = ""):
        """Update an existing test step."""
        endpoint = f"/rest/zapi/latest/teststep/{issue_id}/{step_id}"
        payload = {"step": step, "data": data, "result": result}
        return await self._request("PUT", endpoint, json_data=payload)

    async def delete_test_step(self, issue_id: str, step_id: int):
        """Delete a specific test step."""
        endpoint = f"/rest/zapi/latest/teststep/{issue_id}/{step_id}"
        return await self._request("DELETE", endpoint)

    async def delete_test_case(self, issue_key: str):
        """Delete a Jira issue (test case)."""
        endpoint = f"/rest/api/2/issue/{issue_key}"
        return await self._request("DELETE", endpoint)
