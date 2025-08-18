from abc import ABC, abstractmethod
from typing import List, Optional
from .entities import WoWArticle, VectorDocument, AIResponse, QuestionRequest


class VectorRepository(ABC):
    @abstractmethod
    async def search_similar(self, query: str, k: int = 5) -> List[VectorDocument]:
        pass
    
    @abstractmethod
    async def add_document(self, document: VectorDocument) -> None:
        pass
    
    @abstractmethod
    async def get_collection_info(self) -> dict:
        pass


class AIRepository(ABC):
    @abstractmethod
    async def generate_response(
        self, 
        question: str, 
        context_documents: List[VectorDocument]
    ) -> AIResponse:
        pass


class MonitoringRepository(ABC):
    @abstractmethod
    async def track_request(
        self,
        request: QuestionRequest,
        response: AIResponse,
        duration_ms: float
    ) -> None:
        pass