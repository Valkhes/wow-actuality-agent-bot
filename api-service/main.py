import asyncio
import structlog
from src.infrastructure.logging import configure_logging
from src.infrastructure.chroma_repository import ChromaVectorRepository
from src.infrastructure.gemini_repository import GeminiAIRepository
from src.infrastructure.litellm_repository import LiteLLMAIRepository
from src.infrastructure.langfuse_repository import LangfuseMonitoringRepository, NoOpMonitoringRepository
from src.application.use_cases import AnswerWoWQuestionUseCase, GetSystemStatusUseCase
from src.presentation.api import WoWAPI
from config import get_settings

# Load settings
settings = get_settings()
logger = structlog.get_logger()


def create_app():
    # Configure logging
    configure_logging(settings.log_level, settings.log_format)
    
    logger.info(
        "Starting WoW API Service",
        environment=settings.environment,
        log_level=settings.log_level,
        chromadb_host=settings.chromadb_host,
        ai_model=settings.ai_model_name
    )
    
    # Create repositories
    vector_repository = ChromaVectorRepository(
        host=settings.chromadb_host,
        port=settings.chromadb_port,
        collection_name=settings.chromadb_collection
    )
    
    # ChromaDB connection will be established on first request
    logger.info("ChromaDB connection will be established on first request")
    
    # Choose AI repository based on configuration
    if settings.litellm_gateway_url:
        logger.info("Using LiteLLM Gateway for AI repository")
        ai_repository = LiteLLMAIRepository(
            gateway_url=settings.litellm_gateway_url,
            model_name=settings.ai_model_name,
            temperature=settings.ai_temperature,
            max_tokens=settings.ai_max_tokens
        )
    else:
        logger.info("Using direct Gemini API for AI repository")
        ai_repository = GeminiAIRepository(
            api_key=settings.google_api_key,
            model_name=settings.ai_model_name,
            temperature=settings.ai_temperature,
            max_tokens=settings.ai_max_tokens
        )
    
    # Create monitoring repository (with fallback)
    try:
        if settings.langfuse_secret_key and settings.langfuse_public_key:
            monitoring_repository = LangfuseMonitoringRepository(
                secret_key=settings.langfuse_secret_key,
                public_key=settings.langfuse_public_key,
                host=settings.langfuse_host
            )
        else:
            monitoring_repository = NoOpMonitoringRepository()
    except Exception as e:
        logger.warning("Failed to setup Langfuse, using no-op monitoring", error=str(e))
        monitoring_repository = NoOpMonitoringRepository()
    
    # Create use cases
    answer_question_use_case = AnswerWoWQuestionUseCase(
        vector_repository=vector_repository,
        ai_repository=ai_repository,
        monitoring_repository=monitoring_repository,
        max_context_documents=settings.max_context_documents
    )
    
    system_status_use_case = GetSystemStatusUseCase(
        vector_repository=vector_repository
    )
    
    # Create API
    api = WoWAPI(
        answer_question_use_case=answer_question_use_case,
        system_status_use_case=system_status_use_case
    )
    
    logger.info("WoW API Service initialized successfully")
    
    return api.app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )