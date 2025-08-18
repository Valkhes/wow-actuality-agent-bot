import asyncio
import discord
import uvicorn
import structlog
from contextlib import asynccontextmanager

from src.infrastructure.logging import configure_logging
from src.infrastructure.api_client import HTTPWoWAPIRepository
from src.infrastructure.rate_limiter import InMemoryRateLimitRepository
from src.application.use_cases import HandleWoWQuestionUseCase
from src.presentation.discord_bot import WoWBot, setup
from src.presentation.health import app as health_app
from config import get_settings

settings = get_settings()
logger = structlog.get_logger()


async def create_bot() -> WoWBot:
    # Configure logging
    configure_logging(settings.log_level, settings.log_format)
    
    # Create repositories
    api_repository = HTTPWoWAPIRepository(settings.api_service_url)
    rate_limit_repository = InMemoryRateLimitRepository(settings.rate_limit_requests_per_minute)
    
    # Create use case
    question_use_case = HandleWoWQuestionUseCase(
        api_repository=api_repository,
        rate_limit_repository=rate_limit_repository,
        max_question_length=settings.max_question_length
    )
    
    # Configure Discord intents
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    
    # Create bot
    bot = WoWBot(
        command_prefix="!",
        intents=intents,
        question_use_case=question_use_case,
        max_response_length=settings.max_response_length
    )
    
    # Setup cog
    await setup(bot)
    
    return bot


async def run_health_server():
    config = uvicorn.Config(
        health_app,
        host="0.0.0.0",
        port=settings.health_check_port,
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    logger.info(
        "Starting WoW Discord Bot",
        environment=settings.environment,
        log_level=settings.log_level,
        max_question_length=settings.max_question_length,
        rate_limit=settings.rate_limit_requests_per_minute
    )
    
    # Create bot
    bot = await create_bot()
    
    # Start health check server and bot concurrently
    try:
        await asyncio.gather(
            bot.start(settings.discord_bot_token),
            run_health_server()
        )
    except KeyboardInterrupt:
        logger.info("Shutting down bot...")
        await bot.close()
    except Exception as e:
        logger.error("Bot crashed", error=str(e), exc_info=True)
        await bot.close()
        raise


if __name__ == "__main__":
    asyncio.run(main())