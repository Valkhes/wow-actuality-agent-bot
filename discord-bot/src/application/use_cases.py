import structlog
from typing import Optional
from ..domain.entities import WoWQuestion, WoWResponse, BotUser
from ..domain.repositories import WoWAPIRepository, RateLimitRepository

logger = structlog.get_logger()


class HandleWoWQuestionUseCase:
    def __init__(
        self,
        api_repository: WoWAPIRepository,
        rate_limit_repository: RateLimitRepository,
        max_question_length: int = 500
    ):
        self.api_repository = api_repository
        self.rate_limit_repository = rate_limit_repository
        self.max_question_length = max_question_length

    async def execute(self, question: WoWQuestion, user: BotUser) -> WoWResponse:
        logger.info(
            "Processing WoW question",
            user_id=user.id,
            username=user.username,
            question_length=len(question.content)
        )
        
        # Validate question length
        if len(question.content) > self.max_question_length:
            raise ValueError(f"Question too long. Maximum {self.max_question_length} characters allowed.")
        
        # Check rate limiting
        if await self.rate_limit_repository.is_rate_limited(user.id):
            raise RateLimitError("Rate limit exceeded. Please wait before asking another question.")
        
        # Record the request
        await self.rate_limit_repository.record_request(user.id)
        
        try:
            # Call the API service
            response = await self.api_repository.ask_question(question)
            
            logger.info(
                "Successfully processed WoW question",
                user_id=user.id,
                response_length=len(response.content),
                source_articles=len(response.source_articles or [])
            )
            
            return response
            
        except Exception as e:
            logger.error(
                "Failed to process WoW question",
                user_id=user.id,
                error=str(e),
                exc_info=True
            )
            raise APIServiceError(f"Failed to get response: {str(e)}")


class RateLimitError(Exception):
    pass


class APIServiceError(Exception):
    pass