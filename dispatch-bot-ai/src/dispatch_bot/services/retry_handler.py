"""
Retry handler with exponential backoff for transient failures.
"""

import asyncio
import random
from typing import Callable, Any


class RetryHandler:
    """Handle retries with exponential backoff"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    async def execute_with_retry(self, func: Callable[[], Any]) -> Any:
        """Execute function with retry logic"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func()
                else:
                    return func()
                    
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    # Exponential backoff with jitter
                    delay = self.base_delay * (2 ** attempt) + random.uniform(0, 0.1)
                    await asyncio.sleep(delay)
                else:
                    # Final attempt failed
                    break
        
        # All retries failed
        raise last_exception