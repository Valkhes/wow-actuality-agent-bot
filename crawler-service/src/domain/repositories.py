from abc import ABC, abstractmethod
from typing import List, Optional, Set
from .entities import WoWArticle, CrawlResult, CrawlerStats


class ArticleRepository(ABC):
    @abstractmethod
    async def save_article(self, article: WoWArticle) -> None:
        pass
    
    @abstractmethod
    async def get_article_by_url(self, url: str) -> Optional[WoWArticle]:
        pass
    
    @abstractmethod
    async def get_processed_urls(self) -> Set[str]:
        pass
    
    @abstractmethod
    async def mark_article_processed(self, article_id: str) -> None:
        pass
    
    @abstractmethod
    async def get_stats(self) -> CrawlerStats:
        pass


class WebScrapingRepository(ABC):
    @abstractmethod
    async def fetch_article_urls(self, base_url: str, max_articles: int) -> List[str]:
        pass
    
    @abstractmethod
    async def extract_article_content(self, url: str) -> Optional[WoWArticle]:
        pass


class VectorStoreRepository(ABC):
    @abstractmethod
    async def store_article(self, article: WoWArticle) -> None:
        pass
    
    @abstractmethod
    async def update_article(self, article: WoWArticle) -> None:
        pass
    
    @abstractmethod
    async def get_collection_info(self) -> dict:
        pass


class CacheRepository(ABC):
    @abstractmethod
    async def get_cached_urls(self) -> Set[str]:
        pass
    
    @abstractmethod
    async def cache_urls(self, urls: Set[str]) -> None:
        pass
    
    @abstractmethod
    async def is_url_processed(self, url: str) -> bool:
        pass
    
    @abstractmethod
    async def mark_url_processed(self, url: str) -> None:
        pass