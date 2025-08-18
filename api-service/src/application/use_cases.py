import time
import structlog
from typing import List
from ..domain.entities import QuestionRequest, AIResponse, VectorDocument
from ..domain.repositories import VectorRepository, AIRepository, MonitoringRepository

logger = structlog.get_logger()


class AnswerWoWQuestionUseCase:
    def __init__(
        self,
        vector_repository: VectorRepository,
        ai_repository: AIRepository,
        monitoring_repository: MonitoringRepository,
        max_context_documents: int = 5
    ):
        self.vector_repository = vector_repository
        self.ai_repository = ai_repository
        self.monitoring_repository = monitoring_repository
        self.max_context_documents = max_context_documents

    async def execute(self, request: QuestionRequest) -> AIResponse:
        start_time = time.time()
        
        logger.info(
            "Processing WoW question",
            user_id=request.user_id,
            username=request.username,
            question=request.question,
            question_length=len(request.question)
        )
        
        try:
            # Search for relevant context documents
            context_documents = await self.vector_repository.search_similar(
                query=request.question,
                k=self.max_context_documents
            )
            
            logger.info(
                "Retrieved context documents",
                user_id=request.user_id,
                document_count=len(context_documents)
            )
            
            # Generate AI response using context
            ai_response = await self.ai_repository.generate_response(
                question=request.question,
                context_documents=context_documents
            )
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Track request for monitoring
            await self.monitoring_repository.track_request(
                request=request,
                response=ai_response,
                duration_ms=duration_ms
            )
            
            logger.info(
                "Successfully generated WoW response",
                user_id=request.user_id,
                response_length=len(ai_response.content),
                source_count=len(ai_response.source_articles),
                duration_ms=duration_ms,
                confidence=ai_response.confidence
            )
            
            return ai_response
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "Failed to process WoW question",
                user_id=request.user_id,
                error=str(e),
                duration_ms=duration_ms,
                exc_info=True
            )
            raise WoWQuestionProcessingError(f"Failed to process question: {str(e)}")


class GetSystemStatusUseCase:
    def __init__(self, vector_repository: VectorRepository):
        self.vector_repository = vector_repository

    async def execute(self) -> dict:
        try:
            collection_info = await self.vector_repository.get_collection_info()
            
            return {
                "status": "healthy",
                "service": "api-service",
                "vector_db": collection_info,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error("Failed to get system status", error=str(e), exc_info=True)
            return {
                "status": "unhealthy",
                "service": "api-service",
                "error": str(e),
                "timestamp": time.time()
            }


class WoWQuestionProcessingError(Exception):
    pass