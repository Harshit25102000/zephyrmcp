from .base import ZephyrBaseClient
from .tests import ZephyrTestClient
from .cycles import ZephyrCycleClient
from .executions import ZephyrExecutionClient

class ZephyrClient(ZephyrTestClient, ZephyrCycleClient, ZephyrExecutionClient):
    """
    Unified Zephyr Client that combines all specialized functional modules.
    Inherits from Test, Cycle, and Execution client mixins.
    """
    def __init__(self, *args, **kwargs):
        # ZephyrBaseClient's __init__ will be called via the inheritance chain
        super().__init__(*args, **kwargs)
