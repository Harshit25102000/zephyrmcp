from typing import Optional, Dict, Any, List
from .base import ZephyrBaseClient

class ZephyrExecutionClient(ZephyrBaseClient):
    """
    Client mixin for Execution Management.
    """
    async def create_execution(self, issue_id: int, cycle_id: int, project_id: int, version_id: int):
        """Assign a test case to a cycle (Create execution)."""
        endpoint = "/rest/zapi/latest/execution"
        data = {
            "issueId": issue_id,
            "cycleId": cycle_id,
            "projectId": project_id,
            "versionId": version_id
        }
        return await self._request("POST", endpoint, json_data=data)

    async def update_execution_status(self, execution_id: int, status_id: int, comment: str = ""):
        """
        Update the status of a test execution.
        Status IDs: 1: Pass, 2: Fail, 3: WIP, 4: Blocked
        """
        endpoint = f"/rest/zapi/latest/execution/{execution_id}/execute"
        data = {"status": status_id, "comment": comment}
        return await self._request("PUT", endpoint, json_data=data)

    async def get_executions_by_cycle(self, cycle_id: int, project_id: int):
        """Fetch all executions within a specific cycle."""
        endpoint = "/rest/zapi/latest/execution"
        params = {"cycleId": cycle_id, "projectId": project_id}
        return await self._request("GET", endpoint, params=params)

    async def get_step_execution_details(self, execution_id: int):
        """Fetch step-level execution details."""
        endpoint = f"/rest/zapi/latest/stepResult"
        params = {"executionId": execution_id}
        return await self._request("GET", endpoint, params=params)

    async def update_step_status(self, step_result_id: int, status_id: int, comment: str = ""):
        """Update step success/failure status."""
        endpoint = f"/rest/zapi/latest/stepResult/{step_result_id}"
        data = {"status": status_id, "comment": comment}
        return await self._request("PUT", endpoint, json_data=data)

    async def add_attachment_to_execution(self, execution_id: int, file_path: str):
        """Upload an attachment to a test execution."""
        endpoint = "/rest/zapi/latest/attachment"
        params = {"entityId": execution_id, "entityType": "EXECUTION"}
        
        file_name = file_path.split("/")[-1].split("\\")[-1]
        with open(file_path, "rb") as f:
            files = {"file": (file_name, f.read())}
            return await self._upload(endpoint, files, params=params)

    async def add_attachment_to_step_result(self, step_result_id: int, file_path: str):
        """Upload an attachment to a test step result."""
        endpoint = "/rest/zapi/latest/attachment"
        params = {"entityId": step_result_id, "entityType": "STEP_RESULT"}
        
        file_name = file_path.split("/")[-1].split("\\")[-1]
        with open(file_path, "rb") as f:
            files = {"file": (file_name, f.read())}
            return await self._upload(endpoint, files, params=params)

    async def bulk_update_status(self, execution_ids: List[int], status_id: int, comment: str = ""):
        """
        Bulk update execution statuses.
        """
        endpoint = "/rest/zapi/latest/execution/bulkOperation"
        data = {
            "executionIds": execution_ids,
            "status": status_id,
            "comment": comment,
            "stepStatusFlag": "true" 
        }
        return await self._request("POST", endpoint, json_data=data)

    def get_execution_link(self, execution_id: int) -> str:
        """
        Generate a direct URL to the Zephyr execution.
        """
        return f"{self.base_url}/secure/enav/#execution/{execution_id}"
