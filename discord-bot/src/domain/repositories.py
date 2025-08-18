from abc import ABC, abstractmethod
from typing import Optional
from .entities import WoWQuestion, WoWResponse


class WoWAPIRepository(ABC):
    @abstractmethod
    async def ask_question(self, question: WoWQuestion) -> WoWResponse:
        pass


class RateLimitRepository(ABC):
    @abstractmethod
    async def is_rate_limited(self, user_id: str) -> bool:
        pass
    
    @abstractmethod
    async def record_request(self, user_id: str) -> None:
        pass