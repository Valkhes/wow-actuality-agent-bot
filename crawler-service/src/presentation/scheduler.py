import asyncio
import schedule
import time
import structlog
from datetime import datetime
from ..application.use_cases import CrawlArticlesUseCase

logger = structlog.get_logger()


class CrawlScheduler:
    def __init__(
        self,
        crawl_articles_use_case: CrawlArticlesUseCase,
        base_url: str,
        interval_hours: int = 24
    ):
        self.crawl_articles_use_case = crawl_articles_use_case
        self.base_url = base_url
        self.interval_hours = interval_hours
        self.running = False

    async def start_scheduler(self):
        """Start the crawler scheduler"""
        logger.info(
            "Starting crawler scheduler",
            base_url=self.base_url,
            interval_hours=self.interval_hours
        )
        
        # Schedule daily crawl
        schedule.every(self.interval_hours).hours.do(self._schedule_crawl)
        
        # Run initial crawl
        await self._perform_crawl()
        
        self.running = True
        
        # Keep scheduler running
        while self.running:
            schedule.run_pending()
            await asyncio.sleep(60)  # Check every minute

    def stop_scheduler(self):
        """Stop the scheduler"""
        logger.info("Stopping crawler scheduler")
        self.running = False

    def _schedule_crawl(self):
        """Schedule a crawl (called by schedule library)"""
        try:
            # Create new event loop for scheduled task
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._perform_crawl())
            loop.close()
        except Exception as e:
            logger.error("Scheduled crawl failed", error=str(e), exc_info=True)

    async def _perform_crawl(self):
        """Perform the actual crawl"""
        try:
            logger.info("Starting scheduled crawl", base_url=self.base_url)
            
            result = await self.crawl_articles_use_case.execute(self.base_url)
            
            logger.info(
                "Scheduled crawl completed",
                articles_discovered=result.articles_discovered,
                articles_processed=result.articles_processed,
                articles_failed=result.articles_failed,
                articles_updated=result.articles_updated,
                duration_seconds=result.duration_seconds,
                success_rate=result.success_rate,
                error_count=len(result.errors)
            )
            
            if result.errors:
                logger.warning("Crawl completed with errors", errors=result.errors[:5])  # Show first 5 errors
            
        except Exception as e:
            logger.error("Crawl execution failed", error=str(e), exc_info=True)