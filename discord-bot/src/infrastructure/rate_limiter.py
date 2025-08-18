import asyncio
import time
from collections import defaultdict, deque
from typing import Dict, Deque
from ..domain.repositories import RateLimitRepository


class InMemoryRateLimitRepository(RateLimitRepository):
    def __init__(self, requests_per_minute: int = 1):
        self.requests_per_minute = requests_per_minute
        self.user_requests: Dict[str, Deque[float]] = defaultdict(deque)
        self.lock = asyncio.Lock()
    
    async def is_rate_limited(self, user_id: str) -> bool:
        async with self.lock:
            current_time = time.time()
            user_queue = self.user_requests[user_id]
            
            # Remove requests older than 1 minute
            while user_queue and current_time - user_queue[0] > 60:
                user_queue.popleft()
            
            # Check if rate limit is exceeded
            return len(user_queue) >= self.requests_per_minute
    
    async def record_request(self, user_id: str) -> None:
        async with self.lock:
            current_time = time.time()
            self.user_requests[user_id].append(current_time)