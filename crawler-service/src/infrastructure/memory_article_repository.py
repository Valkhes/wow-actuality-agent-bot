from datetime import datetime
from typing import Dict, List, Optional, Set
import structlog
from ..domain.entities import WoWArticle, CrawlerStats, ArticleStatus
from ..domain.repositories import ArticleRepository

logger = structlog.get_logger()


class InMemoryArticleRepository(ArticleRepository):
    """In-memory article repository for simple storage"""
    
    def __init__(self):
        self.articles: Dict[str, WoWArticle] = {}
        self.url_to_id: Dict[str, str] = {}
        self.start_time = datetime.now()

    async def save_article(self, article: WoWArticle) -> None:
        """Save article to memory"""
        try:
            self.articles[article.id] = article
            self.url_to_id[str(article.url)] = article.id
            
            logger.debug(
                "Saved article to memory",
                article_id=article.id,
                title=article.title[:50] + "..." if len(article.title) > 50 else article.title,
                status=article.status
            )
            
        except Exception as e:
            logger.error(
                "Failed to save article",
                article_id=article.id,
                error=str(e),
                exc_info=True
            )
            raise

    async def get_article_by_url(self, url: str) -> Optional[WoWArticle]:
        """Get article by URL"""
        try:
            article_id = self.url_to_id.get(url)
            if article_id:
                return self.articles.get(article_id)
            return None
            
        except Exception as e:
            logger.error("Failed to get article by URL", url=url, error=str(e))
            return None

    async def get_processed_urls(self) -> Set[str]:
        """Get set of processed URLs"""
        try:
            return set(self.url_to_id.keys())
        except Exception as e:
            logger.error("Failed to get processed URLs", error=str(e))
            return set()

    async def mark_article_processed(self, article_id: str) -> None:
        """Mark article as processed"""
        try:
            if article_id in self.articles:
                article = self.articles[article_id]
                updated_article = article.copy(update={"status": ArticleStatus.PROCESSED})
                self.articles[article_id] = updated_article
                
                logger.debug("Marked article as processed", article_id=article_id)
        except Exception as e:
            logger.error("Failed to mark article as processed", article_id=article_id, error=str(e))

    async def get_stats(self) -> CrawlerStats:
        """Get crawler statistics"""
        try:
            total_articles = len(self.articles)
            successful_crawls = len([a for a in self.articles.values() if a.status in [ArticleStatus.PROCESSED, ArticleStatus.UPDATED]])
            failed_crawls = len([a for a in self.articles.values() if a.status == ArticleStatus.FAILED])
            
            # Calculate uptime
            uptime_hours = (datetime.now() - self.start_time).total_seconds() / 3600
            
            # Find last crawl time
            last_crawl = None
            if self.articles:
                last_crawl = max(article.discovered_date for article in self.articles.values())
            
            # Calculate average articles per crawl (simplified)
            average_articles = total_articles / max(1, successful_crawls + failed_crawls) if total_articles > 0 else 0
            
            return CrawlerStats(
                total_articles=total_articles,
                successful_crawls=successful_crawls,
                failed_crawls=failed_crawls,
                last_crawl=last_crawl,
                average_articles_per_crawl=round(average_articles, 2),
                uptime_hours=round(uptime_hours, 2)
            )
            
        except Exception as e:
            logger.error("Failed to get stats", error=str(e), exc_info=True)
            return CrawlerStats(
                total_articles=0,
                successful_crawls=0,
                failed_crawls=0
            )