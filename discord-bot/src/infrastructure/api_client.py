import aiohttp
import structlog
from typing import Optional
from ..domain.entities import WoWQuestion, WoWResponse
from ..domain.repositories import WoWAPIRepository

logger = structlog.get_logger()


class HTTPWoWAPIRepository(WoWAPIRepository):
    def __init__(self, api_base_url: str, timeout: int = 30):
        self.api_base_url = api_base_url.rstrip('/')
        self.timeout = aiohttp.ClientTimeout(total=timeout)
    
    async def ask_question(self, question: WoWQuestion) -> WoWResponse:
        url = f"{self.api_base_url}/ask"
        
        payload = {
            "question": question.content,
            "user_id": question.user_id,
            "username": question.username,
            "channel_id": question.channel_id,
            "guild_id": question.guild_id,
            "timestamp": question.timestamp.isoformat()
        }
        
        logger.info("Sending request to API service", url=url, user_id=question.user_id)
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        return WoWResponse(
                            content=data["response"],
                            source_articles=data.get("source_articles", []),
                            confidence=data.get("confidence")
                        )
                    else:
                        error_text = await response.text()
                        logger.error(
                            "API service returned error",
                            status=response.status,
                            error=error_text,
                            user_id=question.user_id
                        )
                        raise Exception(f"API service error ({response.status}): {error_text}")
                        
        except aiohttp.ClientError as e:
            logger.error(
                "HTTP client error when calling API service",
                error=str(e),
                user_id=question.user_id,
                exc_info=True
            )
            raise Exception(f"Failed to connect to API service: {str(e)}")
        except Exception as e:
            logger.error(
                "Unexpected error when calling API service",
                error=str(e),
                user_id=question.user_id,
                exc_info=True
            )
            raise