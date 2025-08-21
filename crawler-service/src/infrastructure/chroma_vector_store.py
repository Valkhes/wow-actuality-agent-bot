import chromadb
from chromadb.config import Settings
import structlog
from typing import List
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
                    # Log article count at startup
                    try:
                        count = self.collection.count()
                        logger.info(
                            "ChromaDB startup status",
                            collection_name=self.collection_name,
                            available_articles=count,
                            status="connected"
                        )
                    except Exception as e:
                        logger.warning("Could not retrieve article count at startup", error=str(e))
                except Exception:
                    self.collection = self.client.create_collection(
                        name=self.collection_name,
                        metadata={"description": "World of Warcraft articles from Blizzspirit"}
                    )
                    logger.info("Created new ChromaDB collection", collection=self.collection_name)
                    # Log article count for new collection (should be 0)
                    logger.info(
                        "ChromaDB startup status",
                        collection_name=self.collection_name,
                        available_articles=0,
                        status="created_new"
                    )
                    
            except Exception as e:
                logger.error("Failed to connect to ChromaDB", error=str(e), exc_info=True)
                raise ConnectionError(f"Cannot connect to ChromaDB: {str(e)}")

    async def store_article(self, article: WoWArticle) -> None:
        """Store article in vector database with improved chunking"""
        await self._ensure_connection()
        
        try:
            # Create chunks from article content
            chunks = self._create_article_chunks(article)
            
            # Store all chunks in a single batch operation
            if chunks:
                documents = [chunk["text"] for chunk in chunks]
                metadatas = [chunk["metadata"] for chunk in chunks]  
                ids = [chunk["id"] for chunk in chunks]
                
                self.collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
            
            # Get updated collection count after adding the article
            try:
                updated_count = self.collection.count()
                logger.info(
                    "Added new article to ChromaDB",
                    article_id=article.id,
                    chunk_count=len(chunks),
                    title=article.title[:50] + "..." if len(article.title) > 50 else article.title,
                    total_articles_in_db=updated_count,
                    collection_name=self.collection_name
                )
            except Exception:
                # Fallback to original logging if count fails
                logger.info(
                    "Stored article chunks in ChromaDB",
                    article_id=article.id,
                    chunk_count=len(chunks),
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
            
            # Get collection count after update
            try:
                collection_count = self.collection.count()
                logger.info(
                    "Updated article in ChromaDB", 
                    article_id=article.id,
                    title=article.title[:50] + "..." if len(article.title) > 50 else article.title,
                    total_articles_in_db=collection_count,
                    collection_name=self.collection_name
                )
            except Exception:
                # Fallback to original logging if count fails
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
    
    def _create_article_chunks(self, article: WoWArticle) -> List[dict]:
        """Create optimized chunks from article content"""
        chunks = []
        
        # Base metadata for all chunks
        base_metadata = {
            "title": article.title,
            "url": str(article.url),
            "author": article.author or "Unknown",
            "category": article.category or "World of Warcraft",
            "published_date": article.published_date.isoformat(),
            "discovered_date": article.discovered_date.isoformat(),
            "tags": ", ".join(article.tags),
            "summary": article.summary or "",
            "article_id": article.id
        }
        
        # Chunk 1: Title + Summary (high-level context)
        title_chunk = {
            "id": f"{article.id}_title",
            "text": f"{article.title}\n\n{article.summary or ''}",
            "metadata": {**base_metadata, "chunk_type": "title_summary"}
        }
        chunks.append(title_chunk)
        
        # Chunk the full content comprehensively - no content should be lost
        content = article.content.strip()
        if content:
            # Use overlapping sliding window approach to ensure complete coverage
            chunk_size = 1500  # Larger chunks for more context
            overlap_size = 300  # Significant overlap to ensure no information loss
            
            chunk_count = 0
            start_pos = 0
            
            while start_pos < len(content):
                # Calculate end position for this chunk
                end_pos = min(start_pos + chunk_size, len(content))
                
                # If not at the end and we'd cut off mid-word, extend to word boundary
                if end_pos < len(content):
                    # Find the last space within reasonable distance to avoid cutting words
                    last_space = content.rfind(' ', end_pos - 100, end_pos)
                    if last_space > start_pos + chunk_size // 2:
                        end_pos = last_space
                
                # Extract chunk content
                chunk_text = content[start_pos:end_pos].strip()
                
                if chunk_text:
                    chunk_count += 1
                    chunks.append({
                        "id": f"{article.id}_content_{chunk_count}",
                        "text": f"{article.title}\n\n{chunk_text}",
                        "metadata": {
                            **base_metadata, 
                            "chunk_type": "content", 
                            "chunk_index": chunk_count,
                            "start_pos": start_pos,
                            "end_pos": end_pos
                        }
                    })
                
                # Move start position for next chunk with overlap
                if end_pos >= len(content):
                    break
                start_pos = max(start_pos + chunk_size - overlap_size, end_pos - overlap_size)
        
        return chunks