from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
import structlog
from typing import Dict, Any
from ..domain.entities import QuestionRequest, AIResponse
from ..application.use_cases import AnswerWoWQuestionUseCase, GetSystemStatusUseCase, WoWQuestionProcessingError

logger = structlog.get_logger()


class WoWAPI:
    def __init__(
        self,
        answer_question_use_case: AnswerWoWQuestionUseCase,
        system_status_use_case: GetSystemStatusUseCase
    ):
        self.app = FastAPI(
            title="WoW Actuality API",
            description="AI-powered World of Warcraft news and information service",
            version="1.0.0"
        )
        self.answer_question_use_case = answer_question_use_case
        self.system_status_use_case = system_status_use_case
        
        self._setup_routes()

    def _setup_routes(self):
        @self.app.post("/ask", response_model=Dict[str, Any])
        async def ask_question(request: QuestionRequest):
            logger.info(
                "Received ask request",
                user_id=request.user_id,
                username=request.username,
                question_length=len(request.question)
            )
            
            try:
                response = await self.answer_question_use_case.execute(request)
                
                return {
                    "response": response.content,
                    "source_articles": response.source_articles,
                    "confidence": response.confidence,
                    "timestamp": response.timestamp.isoformat()
                }
                
            except WoWQuestionProcessingError as e:
                logger.error(
                    "Question processing error",
                    user_id=request.user_id,
                    error=str(e)
                )
                raise HTTPException(status_code=500, detail=str(e))
                
            except Exception as e:
                logger.error(
                    "Unexpected error in ask endpoint",
                    user_id=request.user_id,
                    error=str(e),
                    exc_info=True
                )
                raise HTTPException(status_code=500, detail="Internal server error")

        @self.app.get("/health")
        async def health_check():
            try:
                status = await self.system_status_use_case.execute()
                return JSONResponse(
                    status_code=200 if status["status"] == "healthy" else 503,
                    content=status
                )
            except Exception as e:
                logger.error("Health check failed", error=str(e), exc_info=True)
                return JSONResponse(
                    status_code=503,
                    content={
                        "status": "unhealthy",
                        "service": "api-service",
                        "error": str(e)
                    }
                )

        @self.app.get("/")
        async def root():
            return {
                "message": "WoW Actuality API",
                "version": "1.0.0",
                "status": "running"
            }

        @self.app.get("/docs-info")
        async def docs_info():
            return {
                "docs_url": "/docs",
                "redoc_url": "/redoc",
                "openapi_url": "/openapi.json"
            }