import httpx
import logging
from typing import Optional, Dict, Any
from src.config import JIRA_BASE_URL, JIRA_TIMEOUT

logger = logging.getLogger("server")

class ZephyrBaseClient:
    """
    Base Client for Zephyr/Jira interaction.
    Handles shared session, authentication, and request logic.
    """
    def __init__(self, 
                 base_url: str = JIRA_BASE_URL, 
                 username: Optional[str] = None, 
                 password: Optional[str] = None, 
                 token: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.timeout = JIRA_TIMEOUT
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
            logger.info("Initializing ZephyrClient with Token Auth")
        elif username and password:
            self.auth = httpx.BasicAuth(username, password)
            logger.info(f"Initializing ZephyrClient with Basic Auth for user: {username}")
        else:
            self.auth = None
            logger.warning("Initializing ZephyrClient without credentials")

    async def _request(self, method: str, endpoint: str, params: Optional[Dict] = None, json_data: Optional[Dict] = None) -> Any:
        url = f"{self.base_url}{endpoint}"
        async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout, auth=getattr(self, 'auth', None)) as client:
            try:
                response = await client.request(method, url, params=params, json=json_data)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP Error {e.response.status_code} for {url}: {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"Request failed for {url}: {str(e)}")
                raise

    async def _upload(self, endpoint: str, files: Dict[str, Any], params: Optional[Dict] = None) -> Any:
        """
        Handle multipart/form-data for attachments.
        """
        url = f"{self.base_url}{endpoint}"
        # We don't set Content-Type header manually for multipart; httpx does it with the correct boundary
        headers = {k: v for k, v in self.headers.items() if k.lower() != "content-type"}
        
        async with httpx.AsyncClient(headers=headers, timeout=self.timeout, auth=getattr(self, 'auth', None)) as client:
            try:
                response = await client.post(url, params=params, files=files)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Upload failed {e.response.status_code} for {url}: {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"Upload exception for {url}: {str(e)}")
                raise
