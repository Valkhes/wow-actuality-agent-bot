import asyncio
import structlog
from datetime import datetime
from typing import List, Set
from ..domain.entities import WoWArticle, CrawlResult, ArticleStatus, CrawlerStats
from ..domain.repositories import (
    ArticleRepository,
    WebScrapingRepository,
    VectorStoreRepository,
    CacheRepository
)

logger = structlog.get_logger()


class CrawlArticlesUseCase:
    def __init__(
        self,
        article_repository: ArticleRepository,
        web_scraping_repository: WebScrapingRepository,
        vector_store_repository: VectorStoreRepository,
        cache_repository: CacheRepository,
        max_articles: int = 100,
        concurrent_requests: int = 5
    ):
        self.article_repository = article_repository
        self.web_scraping_repository = web_scraping_repository
        self.vector_store_repository = vector_store_repository
        self.cache_repository = cache_repository
        self.max_articles = max_articles
        self.concurrent_requests = concurrent_requests
        self.semaphore = asyncio.Semaphore(concurrent_requests)

    async def execute(self, base_url: str) -> CrawlResult:
        start_time = datetime.now()
        errors = []
        
        logger.info(
            "Starting article crawl",
            base_url=base_url,
            max_articles=self.max_articles,
            concurrent_requests=self.concurrent_requests
        )
        
        try:
            # Get list of article URLs from homepage
            article_urls = await self.web_scraping_repository.fetch_article_urls(
                base_url, self.max_articles
            )
            
            logger.info("Discovered article URLs", count=len(article_urls))
            
            # Filter out already processed URLs
            processed_urls = await self.cache_repository.get_cached_urls()
            new_urls = [url for url in article_urls if url not in processed_urls]
            
            logger.info(
                "Filtered URLs",
                total_discovered=len(article_urls),
                already_processed=len(article_urls) - len(new_urls),
                new_to_process=len(new_urls)
            )
            
            # Process articles concurrently
            tasks = [
                self._process_article_url(url)
                for url in new_urls
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count results
            articles_processed = 0
            articles_failed = 0
            articles_updated = 0
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    errors.append(f"URL {new_urls[i]}: {str(result)}")
                    articles_failed += 1
                elif result == "processed":
                    articles_processed += 1
                elif result == "updated":
                    articles_updated += 1
                elif result == "failed":
                    articles_failed += 1
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            crawl_result = CrawlResult(
                articles_discovered=len(article_urls),
                articles_processed=articles_processed,
                articles_failed=articles_failed,
                articles_updated=articles_updated,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                errors=errors
            )
            
            logger.info(
                "Completed article crawl",
                articles_discovered=crawl_result.articles_discovered,
                articles_processed=crawl_result.articles_processed,
                articles_failed=crawl_result.articles_failed,
                articles_updated=crawl_result.articles_updated,
                duration_seconds=crawl_result.duration_seconds,
                success_rate=crawl_result.success_rate,
                error_count=len(errors)
            )
            
            return crawl_result
            
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.error(
                "Crawl failed with unexpected error",
                error=str(e),
                duration_seconds=duration,
                exc_info=True
            )
            
            return CrawlResult(
                articles_discovered=0,
                articles_processed=0,
                articles_failed=0,
                articles_updated=0,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                errors=[str(e)]
            )

    async def _process_article_url(self, url: str) -> str:
        async with self.semaphore:
            try:
                # Check if already processed
                if await self.cache_repository.is_url_processed(url):
                    return "skipped"
                
                # Extract article content
                article = await self.web_scraping_repository.extract_article_content(url)
                
                if not article:
                    await self.cache_repository.mark_url_processed(url)
                    return "failed"
                
                # Check if article already exists (for updates)
                existing_article = await self.article_repository.get_article_by_url(str(article.url))
                
                if existing_article:
                    # Update existing article if content changed
                    if existing_article.content != article.content:
                        updated_article = article.copy(update={
                            "status": ArticleStatus.UPDATED,
                            "id": existing_article.id
                        })
                        await self.article_repository.save_article(updated_article)
                        await self.vector_store_repository.update_article(updated_article)
                        await self.cache_repository.mark_url_processed(url)
                        return "updated"
                    else:
                        await self.cache_repository.mark_url_processed(url)
                        return "skipped"
                else:
                    # Save new article
                    article = article.copy(update={"status": ArticleStatus.PROCESSED})
                    await self.article_repository.save_article(article)
                    await self.vector_store_repository.store_article(article)
                    await self.cache_repository.mark_url_processed(url)
                    return "processed"
                
            except Exception as e:
                logger.error(
                    "Failed to process article",
                    url=url,
                    error=str(e),
                    exc_info=True
                )
                await self.cache_repository.mark_url_processed(url)
                return "failed"


class GetCrawlerStatsUseCase:
    def __init__(
        self,
        article_repository: ArticleRepository,
        vector_store_repository: VectorStoreRepository
    ):
        self.article_repository = article_repository
        self.vector_store_repository = vector_store_repository

    async def execute(self) -> dict:
        try:
            # Get crawler stats
            stats = await self.article_repository.get_stats()
            
            # Get vector store info
            vector_info = await self.vector_store_repository.get_collection_info()
            
            return {
                "crawler_stats": stats.dict(),
                "vector_store": vector_info,
                "status": "healthy"
            }
            
        except Exception as e:
            logger.error("Failed to get crawler stats", error=str(e), exc_info=True)
            return {
                "status": "error",
                "error": str(e)
            }