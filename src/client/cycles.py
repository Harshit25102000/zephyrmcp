from typing import Optional, Dict, Any
from .base import ZephyrBaseClient

class ZephyrCycleClient(ZephyrBaseClient):
    """
    Client mixin for Cycle and Project Management.
    """
    async def create_test_cycle(self, name: str, project_id: int, version_id: int, 
                          cloned_cycle_id: str = "", build: str = "", 
                          environment: str = "QA", description: str = "",
                          start_date: str = "", end_date: str = ""):
        """
        Create or Clone a test cycle with detailed parameters.
        """
        endpoint = "/rest/zapi/latest/cycle"
        data = {
            "name": name,
            "projectId": project_id,
            "versionId": version_id,
            "description": description,
            "build": build,
            "environment": environment,
            "startDate": start_date,
            "endDate": end_date
        }
        if cloned_cycle_id:
            data["clonedCycleId"] = cloned_cycle_id
            
        return await self._request("POST", endpoint, json_data=data)

    async def get_cycles(self, project_id: int, version_id: int):
        """Get all cycles for a particular fix version."""
        endpoint = "/rest/zapi/latest/cycle"
        return await self._request("GET", endpoint, params={"projectId": project_id, "versionId": version_id})

    async def get_issue_statuses(self, project_id: int):
        """Fetch issue statuses for a project."""
        endpoint = "/rest/zapi/latest/zchart/issueStatuses"
        return await self._request("GET", endpoint, params={"projectId": project_id})

    async def get_projects(self):
        """Fetch list of all projects."""
        endpoint = "/rest/zapi/latest/util/project-list"
        return await self._request("GET", endpoint)

    async def clone_cycle(self, name: str, project_id: int, version_id: int, cloned_cycle_id: str, 
                          build: str = "", environment: str = "QA", description: str = "",
                          start_date: str = "", end_date: str = ""):
        """
        Specialized clone operation using the detailed create_test_cycle logic.
        """
        return await self.create_test_cycle(name, project_id, version_id, cloned_cycle_id, 
                                            build, environment, description, start_date, end_date)

    async def get_release_summary(self, project_id: int, version_id: int):
        """
        Detailed summary of the release for UI parity.
        """
        endpoint = "/rest/zapi/latest/util/release-summary"
        params = {"projectId": project_id, "versionId": version_id}
        return await self._request("GET", endpoint, params=params)

    async def delete_cycle(self, cycle_id: int):
        """Delete a specific test cycle."""
        endpoint = f"/rest/zapi/latest/cycle/{cycle_id}"
        return await self._request("DELETE", endpoint)

    async def update_cycle(self, cycle_id: int, data: Dict[str, Any]):
        """Update properties of an existing cycle."""
        endpoint = f"/rest/zapi/latest/cycle"
        # Often ZAPI uses a PUT to /cycle for updates if cycleId is in payload
        payload = {"id": cycle_id, **data}
        return await self._request("PUT", endpoint, json_data=payload)

    async def add_folder(self, name: str, parent_cycle_id: int, project_id: int, version_id: int):
        """Add a folder within a cycle."""
        endpoint = "/rest/zapi/latest/folder/create"
        data = {
            "name": name,
            "cycleId": parent_cycle_id,
            "projectId": project_id,
            "versionId": version_id
        }
        return await self._request("POST", endpoint, json_data=data)
