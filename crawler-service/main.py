import asyncio
import uvicorn
import structlog
from contextlib import asynccontextmanager

from src.infrastructure.logging import configure_logging
from src.infrastructure.blizzspirit_scraper import BlizzSpiritScrapingRepository
from src.infrastructure.chroma_vector_store import ChromaVectorStoreRepository
from src.infrastructure.memory_article_repository import InMemoryArticleRepository
from src.infrastructure.file_cache import FileCacheRepository
from src.application.use_cases import CrawlArticlesUseCase, GetCrawlerStatsUseCase
from src.presentation.api import CrawlerAPI
from src.presentation.scheduler import CrawlScheduler
from config import get_settings

# Load settings
settings = get_settings()
logger = structlog.get_logger()

# Global scheduler reference
scheduler = None


@asynccontextmanager
async def lifespan(app):
    """Application lifespan handler"""
    global scheduler
    
    logger.info("Starting crawler service")
    
    # Start scheduler
    scheduler_task = asyncio.create_task(scheduler.start_scheduler())
    
    yield
    
    # Cleanup
    logger.info("Shutting down crawler service")
    if scheduler:
        scheduler.stop_scheduler()
    scheduler_task.cancel()


def create_app():
    global scheduler
    
    # Configure logging
    configure_logging(settings.log_level, settings.log_format)
    
    logger.info(
        "Starting WoW Crawler Service",
        environment=settings.environment,
        log_level=settings.log_level,
        base_url=settings.blizzspirit_base_url,
        interval_hours=settings.crawler_interval_hours,
        max_articles=settings.crawler_max_articles
    )
    
    # Create repositories
    web_scraping_repository = BlizzSpiritScrapingRepository(
        base_url=settings.blizzspirit_base_url,
        requests_per_second=settings.requests_per_second,
        timeout=settings.request_timeout
    )
    
    vector_store_repository = ChromaVectorStoreRepository(
        host=settings.chromadb_host,
        port=settings.chromadb_port,
        collection_name=settings.chromadb_collection
    )
    
    article_repository = InMemoryArticleRepository()
    
    cache_repository = FileCacheRepository(
        cache_file=settings.cache_file
    )
    
    # Create use cases
    crawl_articles_use_case = CrawlArticlesUseCase(
        article_repository=article_repository,
        web_scraping_repository=web_scraping_repository,
        vector_store_repository=vector_store_repository,
        cache_repository=cache_repository,
        max_articles=settings.crawler_max_articles,
        concurrent_requests=settings.concurrent_requests
    )
    
    get_stats_use_case = GetCrawlerStatsUseCase(
        article_repository=article_repository,
        vector_store_repository=vector_store_repository
    )
    
    # Create scheduler
    scheduler = CrawlScheduler(
        crawl_articles_use_case=crawl_articles_use_case,
        base_url=settings.blizzspirit_base_url,
        interval_hours=settings.crawler_interval_hours
    )
    
    # Create API
    api = CrawlerAPI(
        crawl_articles_use_case=crawl_articles_use_case,
        get_stats_use_case=get_stats_use_case,
        base_url=settings.blizzspirit_base_url
    )
    
    # Configure lifespan
    api.app.router.lifespan_context = lifespan
    
    logger.info("WoW Crawler Service initialized successfully")
    
    return api.app


app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )