"""
Rate limiting service for API protection and fair usage.
"""

import time
from typing import Dict, NamedTuple
from collections import defaultdict, deque


class RetryInfo(NamedTuple):
    """Information about when to retry"""
    seconds_until_reset: int
    requests_remaining: int


class RateLimiter:
    """Simple rate limiter for protecting against abuse"""
    
    def __init__(self, max_requests_per_minute: int = 60):
        self.max_requests = max_requests_per_minute
        self.requests: Dict[str, deque] = defaultdict(lambda: deque())
    
    def is_request_allowed(self, user_id: str) -> bool:
        """Check if request is allowed for user"""
        now = time.time()
        user_requests = self.requests[user_id]
        
        # Remove requests older than 1 minute
        while user_requests and user_requests[0] < now - 60:
            user_requests.popleft()
        
        # Check if under limit
        if len(user_requests) < self.max_requests:
            user_requests.append(now)
            return True
        
        return False
    
    def get_retry_info(self, user_id: str) -> RetryInfo:
        """Get retry information for user"""
        now = time.time()
        user_requests = self.requests[user_id]
        
        if not user_requests:
            return RetryInfo(0, self.max_requests)
        
        # Time until oldest request expires
        oldest_request = user_requests[0]
        seconds_until_reset = max(0, int(60 - (now - oldest_request)))
        requests_remaining = max(0, self.max_requests - len(user_requests))
        
        return RetryInfo(seconds_until_reset, requests_remaining)