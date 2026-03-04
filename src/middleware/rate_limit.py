import time
import logging
from typing import Dict, List
from src.config import RATE_LIMIT_COUNT, RATE_LIMIT_WINDOW_SECONDS

logger = logging.getLogger("server")

class RateLimiter:
    """
    Sliding Window Rate Limiter to prevent misuse.
    Tracks usage per user/token based on a timeframe (window) in seconds.
    """
    def __init__(self, limit: int = RATE_LIMIT_COUNT, window: int = RATE_LIMIT_WINDOW_SECONDS):
        self.limit = limit
        self.window = window
        # Buckets stored as {identifier: [timestamp1, timestamp2, ...]}
        self.user_requests: Dict[str, List[float]] = {}

    def is_allowed(self, identifier: str) -> bool:
        """
        Checks if a request from 'identifier' is allowed within the current window.
        """
        now = time.time()
        
        if identifier not in self.user_requests:
            self.user_requests[identifier] = [now]
            return True

        # Clean up timestamps older than the window
        expiry_time = now - self.window
        self.user_requests[identifier] = [
            ts for ts in self.user_requests[identifier] if ts > expiry_time
        ]

        if len(self.user_requests[identifier]) < self.limit:
            self.user_requests[identifier].append(now)
            return True
        
        logger.warning(
            f"Rate limit exceeded for {identifier}: "
            f"{len(self.user_requests[identifier])} requests in {self.window}s window "
            f"(Limit: {self.limit})"
        )
        return False
