from google.cloud import firestore
from google.cloud.firestore import Client
from typing import Set, Optional
import structlog
from ..domain.repositories import CacheRepository

logger = structlog.get_logger()


class FirestoreCacheRepository(CacheRepository):
    def __init__(
        self, 
        project_id: Optional[str] = None, 
        collection_name: str = "crawler_cache"
    ):
        self.project_id = project_id
        self.collection_name = collection_name
        self.document_id = "processed_urls"  # Single document to store all URLs
        self.client: Optional[Client] = None

    async def _ensure_connection(self):
        """Ensure connection to Firestore"""
        if self.client is None:
            try:
                self.client = firestore.Client(project=self.project_id)
                logger.debug("Connected to Firestore for cache", collection=self.collection_name)
            except Exception as e:
                logger.error("Failed to connect to Firestore for cache", error=str(e))
                raise ConnectionError(f"Cannot connect to Firestore: {str(e)}")

    async def get_cached_urls(self) -> Set[str]:
        """Load cached URLs from Firestore"""
        try:
            await self._ensure_connection()
            
            doc_ref = self.client.collection(self.collection_name).document(self.document_id)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                urls = data.get('processed_urls', [])
                logger.debug("Loaded URLs from Firestore cache", count=len(urls))
                return set(urls)
            else:
                logger.debug("No cache document found, returning empty set")
                return set()
                
        except Exception as e:
            logger.error("Failed to load cache from Firestore", error=str(e))
            return set()

    async def cache_urls(self, urls: Set[str]) -> None:
        """Save URLs to Firestore cache"""
        try:
            await self._ensure_connection()
            
            doc_ref = self.client.collection(self.collection_name).document(self.document_id)
            
            # Convert set to list for JSON serialization
            data = {
                'processed_urls': list(urls),
                'last_updated': firestore.SERVER_TIMESTAMP,
                'count': len(urls)
            }
            
            doc_ref.set(data)
            logger.debug("Saved URLs to Firestore cache", count=len(urls))
            
        except Exception as e:
            logger.error("Failed to save cache to Firestore", error=str(e))

    async def is_url_processed(self, url: str) -> bool:
        """Check if URL has been processed"""
        cached_urls = await self.get_cached_urls()
        return url in cached_urls

    async def mark_url_processed(self, url: str) -> None:
        """Mark URL as processed"""
        try:
            await self._ensure_connection()
            
            # Use Firestore array union to add the URL atomically
            doc_ref = self.client.collection(self.collection_name).document(self.document_id)
            
            doc_ref.update({
                'processed_urls': firestore.ArrayUnion([url]),
                'last_updated': firestore.SERVER_TIMESTAMP
            })
            
            logger.debug("Marked URL as processed in Firestore", url=url)
            
        except Exception as e:
            # Fallback to loading all URLs and saving them back
            logger.warning(
                "Failed to atomically update cache, falling back to full reload", 
                error=str(e)
            )
            cached_urls = await self.get_cached_urls()
            cached_urls.add(url)
            await self.cache_urls(cached_urls)

    async def clear_cache(self) -> None:
        """Clear all cached URLs"""
        try:
            await self._ensure_connection()
            
            doc_ref = self.client.collection(self.collection_name).document(self.document_id)
            doc_ref.delete()
            
            logger.info("Cleared Firestore cache")
            
        except Exception as e:
            logger.error("Failed to clear Firestore cache", error=str(e))

    async def get_cache_stats(self) -> dict:
        """Get cache statistics"""
        try:
            await self._ensure_connection()
            
            doc_ref = self.client.collection(self.collection_name).document(self.document_id)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                return {
                    'total_urls': len(data.get('processed_urls', [])),
                    'last_updated': data.get('last_updated'),
                    'status': 'active'
                }
            else:
                return {
                    'total_urls': 0,
                    'last_updated': None,
                    'status': 'empty'
                }
                
        except Exception as e:
            logger.error("Failed to get cache stats", error=str(e))
            return {
                'total_urls': 0,
                'last_updated': None,
                'status': 'error',
                'error': str(e)
            }