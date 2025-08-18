import structlog
from typing import Optional
from langfuse import Langfuse
from ..domain.entities import QuestionRequest, AIResponse
from ..domain.repositories import MonitoringRepository

logger = structlog.get_logger()


class LangfuseMonitoringRepository(MonitoringRepository):
    def __init__(
        self,
        secret_key: str,
        public_key: str,
        host: str = "http://langfuse:3000"
    ):
        try:
            self.langfuse = Langfuse(
                secret_key=secret_key,
                public_key=public_key,
                host=host
            )
            logger.info("Initialized Langfuse monitoring", host=host)
        except Exception as e:
            logger.warning("Failed to initialize Langfuse", error=str(e))
            self.langfuse = None

    async def track_request(
        self,
        request: QuestionRequest,
        response: AIResponse,
        duration_ms: float
    ) -> None:
        if not self.langfuse:
            logger.debug("Langfuse not available, skipping tracking")
            return
        
        try:
            # Create a trace for the complete interaction
            trace = self.langfuse.trace(
                name="wow_question_answer",
                user_id=request.user_id,
                metadata={
                    "username": request.username,
                    "guild_id": request.guild_id,
                    "channel_id": request.channel_id,
                    "question_length": len(request.question),
                    "response_length": len(response.content),
                    "source_articles_count": len(response.source_articles),
                    "confidence": response.confidence,
                    "duration_ms": duration_ms
                }
            )
            
            # Track the question as input
            trace.span(
                name="question_processing",
                input={
                    "question": request.question,
                    "timestamp": request.timestamp.isoformat()
                },
                output={
                    "response": response.content,
                    "source_articles": response.source_articles,
                    "confidence": response.confidence
                },
                metadata={
                    "model": "gemini-2.0-flash-exp",
                    "context_documents": len(response.source_articles)
                }
            )
            
            # Track token usage if available (approximate)
            estimated_input_tokens = len(request.question.split()) + 100  # Approximate for context
            estimated_output_tokens = len(response.content.split())
            
            trace.generation(
                name="gemini_generation",
                input=request.question,
                output=response.content,
                model="gemini-2.0-flash-exp",
                usage={
                    "input": estimated_input_tokens,
                    "output": estimated_output_tokens,
                    "total": estimated_input_tokens + estimated_output_tokens
                },
                metadata={
                    "confidence": response.confidence,
                    "duration_ms": duration_ms
                }
            )
            
            logger.info(
                "Tracked request in Langfuse",
                user_id=request.user_id,
                trace_id=trace.id,
                duration_ms=duration_ms
            )
            
        except Exception as e:
            logger.error(
                "Failed to track request in Langfuse",
                user_id=request.user_id,
                error=str(e),
                exc_info=True
            )


class NoOpMonitoringRepository(MonitoringRepository):
    """Fallback monitoring repository that does nothing"""
    
    async def track_request(
        self,
        request: QuestionRequest,
        response: AIResponse,
        duration_ms: float
    ) -> None:
        logger.debug(
            "No-op monitoring: request tracked locally only",
            user_id=request.user_id,
            duration_ms=duration_ms
        )