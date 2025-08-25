from google.cloud import firestore
from google.cloud.firestore import Client
import structlog
from typing import List, Optional
import hashlib
import re
from ..domain.entities import WoWArticle
from ..domain.repositories import VectorStoreRepository

logger = structlog.get_logger()


class FirestoreVectorStoreRepository(VectorStoreRepository):
    def __init__(
        self,
        project_id: Optional[str] = None,
        collection_name: str = "wow_articles"
    ):
        self.project_id = project_id
        self.collection_name = collection_name
        self.client: Optional[Client] = None

    async def _ensure_connection(self):
        """Ensure connection to Firestore"""
        if self.client is None:
            try:
                self.client = firestore.Client(project=self.project_id)
                
                # Test connection
                collection_ref = self.client.collection(self.collection_name)
                
                # Log article count at startup
                try:
                    count_query = collection_ref.count()
                    count_result = count_query.get()
                    count = count_result[0][0].value if count_result else 0
                    
                    logger.info(
                        "Firestore startup status",
                        collection_name=self.collection_name,
                        available_articles=count,
                        status="connected"
                    )
                except Exception as e:
                    logger.warning("Could not retrieve article count at startup", error=str(e))
                    
            except Exception as e:
                logger.error("Failed to connect to Firestore", error=str(e), exc_info=True)
                raise ConnectionError(f"Cannot connect to Firestore: {str(e)}")

    async def store_article(self, article: WoWArticle) -> None:
        """Store article in Firestore with improved chunking"""
        await self._ensure_connection()
        
        try:
            collection_ref = self.client.collection(self.collection_name)
            
            # Create chunks from article content
            chunks = self._create_article_chunks(article)
            
            # Store all chunks using batch operations for better performance
            batch = self.client.batch()
            
            for chunk in chunks:
                doc_ref = collection_ref.document(chunk["id"])
                chunk_data = {
                    "text": chunk["text"],
                    **chunk["metadata"],
                    "keywords": self._extract_keywords(chunk["text"]),
                    "created_at": firestore.SERVER_TIMESTAMP
                }
                batch.set(doc_ref, chunk_data)
            
            # Commit batch
            batch.commit()
            
            # Log success
            try:
                count_query = collection_ref.count()
                count_result = count_query.get()
                updated_count = count_result[0][0].value if count_result else 0
                
                logger.info(
                    "Added new article to Firestore",
                    article_id=article.id,
                    chunk_count=len(chunks),
                    title=article.title[:50] + "..." if len(article.title) > 50 else article.title,
                    total_articles_in_db=updated_count,
                    collection_name=self.collection_name
                )
            except Exception:
                # Fallback to original logging if count fails
                logger.info(
                    "Stored article chunks in Firestore",
                    article_id=article.id,
                    chunk_count=len(chunks),
                    title=article.title[:50] + "..." if len(article.title) > 50 else article.title
                )
            
        except Exception as e:
            logger.error(
                "Failed to store article in Firestore",
                article_id=article.id,
                title=article.title,
                error=str(e),
                exc_info=True
            )
            raise

    async def update_article(self, article: WoWArticle) -> None:
        """Update existing article in Firestore"""
        await self._ensure_connection()
        
        try:
            collection_ref = self.client.collection(self.collection_name)
            
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
                "last_updated": article.discovered_date.isoformat(),
                "keywords": self._extract_keywords(document_text),
                "updated_at": firestore.SERVER_TIMESTAMP
            }
            
            # Update in collection (Firestore will replace if ID exists)
            doc_ref = collection_ref.document(article.id)
            doc_ref.set({
                "text": document_text,
                **metadata
            })
            
            # Log success
            try:
                count_query = collection_ref.count()
                count_result = count_query.get()
                collection_count = count_result[0][0].value if count_result else 0
                
                logger.info(
                    "Updated article in Firestore", 
                    article_id=article.id,
                    title=article.title[:50] + "..." if len(article.title) > 50 else article.title,
                    total_articles_in_db=collection_count,
                    collection_name=self.collection_name
                )
            except Exception:
                # Fallback to original logging if count fails
                logger.info(
                    "Updated article in Firestore",
                    article_id=article.id,
                    title=article.title[:50] + "..." if len(article.title) > 50 else article.title
                )
            
        except Exception as e:
            logger.error(
                "Failed to update article in Firestore",
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
            collection_ref = self.client.collection(self.collection_name)
            count_query = collection_ref.count()
            count_result = count_query.get()
            count = count_result[0][0].value if count_result else 0
            
            return {
                "collection_name": self.collection_name,
                "document_count": count,
                "status": "connected",
                "type": "firestore"
            }
            
        except Exception as e:
            logger.error("Failed to get collection info", error=str(e), exc_info=True)
            return {
                "collection_name": self.collection_name,
                "status": "error",
                "error": str(e),
                "type": "firestore"
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

    def _extract_keywords(self, content: str) -> List[str]:
        """Extract keywords from content for better searchability"""
        # Simple keyword extraction - you might want to use more sophisticated methods
        words = re.findall(r'\b\w{4,}\b', content.lower())
        
        # Remove common stop words
        stop_words = {
            "this", "that", "with", "have", "will", "from", "they", "know", 
            "want", "been", "good", "much", "some", "time", "very", "when",
            "come", "here", "just", "like", "long", "make", "many", "over",
            "such", "take", "than", "them", "well", "were", "what", "dans",
            "pour", "avec", "cette", "sont", "plus", "tout", "tous", "leur",
            "leurs", "peut", "fait", "après", "avant", "depuis", "pendant"
        }
        
        keywords = [word for word in set(words) if word not in stop_words]
        return keywords[:50]  # Limit keywords