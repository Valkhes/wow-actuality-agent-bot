from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
import structlog
from datetime import datetime
from ..application.use_cases import CrawlArticlesUseCase, GetCrawlerStatsUseCase

logger = structlog.get_logger()


class CrawlerAPI:
    def __init__(
        self,
        crawl_articles_use_case: CrawlArticlesUseCase,
        get_stats_use_case: GetCrawlerStatsUseCase,
        base_url: str
    ):
        self.app = FastAPI(
            title="WoW Crawler Service",
            description="Web crawler for World of Warcraft articles from Blizzspirit",
            version="1.0.0"
        )
        self.crawl_articles_use_case = crawl_articles_use_case
        self.get_stats_use_case = get_stats_use_case
        self.base_url = base_url
        self.last_crawl_time = None
        
        self._setup_routes()

    def _setup_routes(self):
        @self.app.get("/health")
        async def health_check():
            try:
                stats = await self.get_stats_use_case.execute()
                return JSONResponse(
                    status_code=200,
                    content={
                        "status": "healthy",
                        "service": "crawler-service",
                        "last_crawl": self.last_crawl_time.isoformat() if self.last_crawl_time else None,
                        "timestamp": datetime.now().isoformat(),
                        **stats
                    }
                )
            except Exception as e:
                logger.error("Health check failed", error=str(e), exc_info=True)
                return JSONResponse(
                    status_code=503,
                    content={
                        "status": "unhealthy",
                        "service": "crawler-service",
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    }
                )

        @self.app.post("/crawl")
        async def trigger_crawl(background_tasks: BackgroundTasks):
            """Manually trigger a crawl operation"""
            try:
                logger.info("Manual crawl triggered")
                background_tasks.add_task(self._perform_crawl)
                
                return {
                    "message": "Crawl started",
                    "timestamp": datetime.now().isoformat(),
                    "status": "started"
                }
                
            except Exception as e:
                logger.error("Failed to start crawl", error=str(e), exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/stats")
        async def get_crawler_stats():
            """Get detailed crawler statistics"""
            try:
                stats = await self.get_stats_use_case.execute()
                stats["last_manual_crawl"] = self.last_crawl_time.isoformat() if self.last_crawl_time else None
                return stats
                
            except Exception as e:
                logger.error("Failed to get stats", error=str(e), exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/")
        async def root():
            return {
                "message": "WoW Crawler Service",
                "version": "1.0.0",
                "status": "running",
                "base_url": self.base_url
            }

    async def _perform_crawl(self):
        """Perform crawl operation in background"""
        try:
            logger.info("Starting background crawl", base_url=self.base_url)
            
            result = await self.crawl_articles_use_case.execute(self.base_url)
            self.last_crawl_time = result.end_time
            
            logger.info(
                "Background crawl completed",
                articles_discovered=result.articles_discovered,
                articles_processed=result.articles_processed,
                articles_failed=result.articles_failed,
                duration_seconds=result.duration_seconds,
                success_rate=result.success_rate
            )
            
        except Exception as e:
            logger.error("Background crawl failed", error=str(e), exc_info=True)