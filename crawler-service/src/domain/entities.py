from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, HttpUrl
from enum import Enum


class ArticleStatus(str, Enum):
    DISCOVERED = "discovered"
    PROCESSED = "processed"
    FAILED = "failed"
    UPDATED = "updated"


class WoWArticle(BaseModel):
    id: str
    title: str
    content: str
    summary: Optional[str] = None
    url: HttpUrl
    published_date: datetime
    discovered_date: datetime = datetime.now()
    status: ArticleStatus = ArticleStatus.DISCOVERED
    tags: List[str] = []
    author: Optional[str] = None
    category: Optional[str] = None
    
    class Config:
        frozen = True


class CrawlResult(BaseModel):
    articles_discovered: int
    articles_processed: int
    articles_failed: int
    articles_updated: int
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    errors: List[str] = []
    
    @property
    def success_rate(self) -> float:
        total = self.articles_discovered
        if total == 0:
            return 1.0
        return self.articles_processed / total


class CrawlerStats(BaseModel):
    total_articles: int
    successful_crawls: int
    failed_crawls: int
    last_crawl: Optional[datetime] = None
    average_articles_per_crawl: float = 0.0
    uptime_hours: float = 0.0