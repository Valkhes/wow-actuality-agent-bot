import chromadb
from chromadb.config import Settings
import structlog
from ..domain.entities import WoWArticle
from ..domain.repositories import VectorStoreRepository

logger = structlog.get_logger()


class ChromaVectorStoreRepository(VectorStoreRepository):
    def __init__(
        self,
        host: str = "chromadb",
        port: int = 8000,
        collection_name: str = "wow_articles"
    ):
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.client = None
        self.collection = None

    async def _ensure_connection(self):
        """Ensure connection to ChromaDB"""
        if self.client is None:
            try:
                self.client = chromadb.HttpClient(
                    host=self.host,
                    port=self.port,
                    settings=Settings(allow_reset=True, anonymized_telemetry=False)
                )
                
                # Get or create collection
                try:
                    self.collection = self.client.get_collection(name=self.collection_name)
                    logger.debug("Connected to existing ChromaDB collection", collection=self.collection_name)
                except Exception:
                    self.collection = self.client.create_collection(
                        name=self.collection_name,
                        metadata={"description": "World of Warcraft articles from Blizzspirit"}
                    )
                    logger.info("Created new ChromaDB collection", collection=self.collection_name)
                    
            except Exception as e:
                logger.error("Failed to connect to ChromaDB", error=str(e), exc_info=True)
                raise ConnectionError(f"Cannot connect to ChromaDB: {str(e)}")

    async def store_article(self, article: WoWArticle) -> None:
        """Store article in vector database"""
        await self._ensure_connection()
        
        try:
            # Prepare document content for embedding
            document_text = f"{article.title}\n\n{article.content}"
            
            # Prepare metadata
            metadata = {
                "title": article.title,
                "url": str(article.url),
                "author": article.author or "Unknown",
                "category": article.category or "World of Warcraft",
                "published_date": article.published_date.isoformat(),
                "discovered_date": article.discovered_date.isoformat(),
                "tags": ", ".join(article.tags),
                "summary": article.summary or ""
            }
            
            # Add to collection
            self.collection.add(
                documents=[document_text],
                metadatas=[metadata],
                ids=[article.id]
            )
            
            logger.info(
                "Stored article in ChromaDB",
                article_id=article.id,
                title=article.title[:50] + "..." if len(article.title) > 50 else article.title
            )
            
        except Exception as e:
            logger.error(
                "Failed to store article in ChromaDB",
                article_id=article.id,
                title=article.title,
                error=str(e),
                exc_info=True
            )
            raise

    async def update_article(self, article: WoWArticle) -> None:
        """Update existing article in vector database"""
        await self._ensure_connection()
        
        try:
            # Prepare updated document content
            document_text = f"{article.title}\n\n{article.content}"
            
            # Prepare updated metadata
            metadata = {
                "title": article.title,
                "url": str(article.url),
                "author": article.author or "Unknown",
                "category": article.category or "World of Warcraft",
                "published_date": article.published_date.isoformat(),
                "discovered_date": article.discovered_date.isoformat(),
                "tags": ", ".join(article.tags),
                "summary": article.summary or "",
                "last_updated": article.discovered_date.isoformat()
            }
            
            # Update in collection (ChromaDB will replace if ID exists)
            self.collection.upsert(
                documents=[document_text],
                metadatas=[metadata],
                ids=[article.id]
            )
            
            logger.info(
                "Updated article in ChromaDB",
                article_id=article.id,
                title=article.title[:50] + "..." if len(article.title) > 50 else article.title
            )
            
        except Exception as e:
            logger.error(
                "Failed to update article in ChromaDB",
                article_id=article.id,
                title=article.title,
                error=str(e),
                exc_info=True
            )
            raise

    async def get_collection_info(self) -> dict:
        """Get information about the collection"""
        await self._ensure_connection()
        
        try:
            count = self.collection.count()
            return {
                "collection_name": self.collection_name,
                "document_count": count,
                "status": "connected",
                "host": f"{self.host}:{self.port}"
            }
            
        except Exception as e:
            logger.error("Failed to get collection info", error=str(e), exc_info=True)
            return {
                "collection_name": self.collection_name,
                "status": "error",
                "error": str(e),
                "host": f"{self.host}:{self.port}"
            }