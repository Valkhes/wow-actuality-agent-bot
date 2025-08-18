import json
import os
from typing import Set
import structlog
from ..domain.repositories import CacheRepository

logger = structlog.get_logger()


class FileCacheRepository(CacheRepository):
    def __init__(self, cache_file: str = "cache/processed_urls.json"):
        self.cache_file = cache_file
        self.cache_dir = os.path.dirname(cache_file)
        self._ensure_cache_dir()

    def _ensure_cache_dir(self):
        """Ensure cache directory exists"""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)

    async def get_cached_urls(self) -> Set[str]:
        """Load cached URLs from file"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return set(data.get('processed_urls', []))
            return set()
        except Exception as e:
            logger.error("Failed to load cache file", error=str(e), cache_file=self.cache_file)
            return set()

    async def cache_urls(self, urls: Set[str]) -> None:
        """Save URLs to cache file"""
        try:
            data = {'processed_urls': list(urls)}
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug("Saved URLs to cache", count=len(urls))
        except Exception as e:
            logger.error("Failed to save cache file", error=str(e), cache_file=self.cache_file)

    async def is_url_processed(self, url: str) -> bool:
        """Check if URL has been processed"""
        cached_urls = await self.get_cached_urls()
        return url in cached_urls

    async def mark_url_processed(self, url: str) -> None:
        """Mark URL as processed"""
        cached_urls = await self.get_cached_urls()
        cached_urls.add(url)
        await self.cache_urls(cached_urls)