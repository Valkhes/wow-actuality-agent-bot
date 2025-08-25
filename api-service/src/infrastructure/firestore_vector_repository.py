from google.cloud import firestore
from google.cloud.firestore import Client
import structlog
from typing import List, Optional, Dict, Any
import hashlib
import re
from ..domain.entities import VectorDocument
from ..domain.repositories import VectorRepository

logger = structlog.get_logger()


class FirestoreVectorRepository(VectorRepository):
    def __init__(
        self,
        project_id: Optional[str] = None,
        collection_name: str = "wow_articles"
    ):
        self.project_id = project_id
        self.collection_name = collection_name
        self.client: Optional[Client] = None

    async def _ensure_connection(self):
        if self.client is None:
            try:
                self.client = firestore.Client(project=self.project_id)
                
                # Test connection
                collection_ref = self.client.collection(self.collection_name)
                
                # Log article count at startup
                try:
                    docs = list(collection_ref.limit(1).stream())
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

    async def search_similar(self, query: str, k: int = 5) -> List[VectorDocument]:
        """
        Search for similar documents using text-based matching.
        Note: This is a simple text search implementation. For true vector similarity,
        consider using Vertex AI Vector Search or embedding-based matching.
        """
        await self._ensure_connection()
        
        try:
            enhanced_queries = self._enhance_query(query)
            
            all_results = []
            collection_ref = self.client.collection(self.collection_name)
            
            # Simple text-based search using Firestore queries
            for enhanced_query in enhanced_queries:
                # Search in content field
                query_words = enhanced_query.lower().split()
                
                for word in query_words:
                    if len(word) > 2:  # Skip very short words
                        # Use array-contains-any for keywords if available
                        try:
                            docs = collection_ref.where("keywords", "array_contains_any", [word]).limit(k).stream()
                            for doc in docs:
                                doc_data = doc.to_dict()
                                doc_data["id"] = doc.id
                                doc_data["matched_query"] = enhanced_query
                                doc_data["similarity_score"] = self._calculate_similarity_score(doc_data.get("content", ""), query)
                                all_results.append(doc_data)
                        except Exception:
                            # Fallback: get all documents and filter in memory (not scalable)
                            docs = collection_ref.limit(50).stream()
                            for doc in docs:
                                doc_data = doc.to_dict()
                                content = doc_data.get("content", "").lower()
                                if word in content:
                                    doc_data["id"] = doc.id
                                    doc_data["matched_query"] = enhanced_query
                                    doc_data["similarity_score"] = self._calculate_similarity_score(content, query)
                                    all_results.append(doc_data)

            # Deduplicate and sort results
            seen_ids = set()
            documents = []
            
            for result in all_results:
                doc_id = result.get("id")
                if doc_id in seen_ids:
                    continue
                seen_ids.add(doc_id)
                
                # Create VectorDocument
                metadata = {k: v for k, v in result.items() if k not in ["content", "id"]}
                
                documents.append(VectorDocument(
                    id=doc_id,
                    content=result.get("content", ""),
                    metadata=metadata
                ))
            
            # Sort by similarity score and limit results
            documents.sort(key=lambda x: x.metadata.get("similarity_score", 0), reverse=True)
            documents = documents[:k]
            
            logger.info(
                "Retrieved similar documents from Firestore",
                query_length=len(query),
                enhanced_queries_count=len(enhanced_queries),
                retrieved_count=len(documents),
                requested_count=k
            )
            
            return documents
            
        except Exception as e:
            logger.error(
                "Failed to search similar documents",
                query=query,
                error=str(e),
                exc_info=True
            )
            return []
    
    def _calculate_similarity_score(self, content: str, query: str) -> float:
        """Simple similarity calculation based on common words"""
        content_words = set(content.lower().split())
        query_words = set(query.lower().split())
        
        if not query_words:
            return 0.0
        
        intersection = content_words & query_words
        return len(intersection) / len(query_words)
    
    def _enhance_query(self, query: str) -> List[str]:
        """Enhance query with variations for better retrieval"""
        enhanced = [query]  # Original query first
        
        query_lower = query.lower()
        query_words = query_lower.split()
        
        # Add individual significant words as separate queries
        significant_words = [word for word in query_words if len(word) > 3]
        for word in significant_words:
            if word not in enhanced:
                enhanced.append(word)
        
        # Add partial matches by removing common French articles/prepositions
        stop_words = ["le", "la", "les", "de", "des", "du", "sur", "pour", "dans", "avec"]
        filtered_words = [word for word in query_words if word not in stop_words]
        if len(filtered_words) > 1:
            filtered_query = " ".join(filtered_words)
            if filtered_query not in enhanced:
                enhanced.append(filtered_query)
        
        # Remove duplicates while preserving order
        seen = set()
        result = []
        for item in enhanced:
            if item.lower() not in seen and item.strip():
                seen.add(item.lower())
                result.append(item)
        
        return result[:3]  # Limit to 3 queries

    async def add_document(self, document: VectorDocument) -> None:
        await self._ensure_connection()
        
        try:
            collection_ref = self.client.collection(self.collection_name)
            
            # Prepare document data
            doc_data = {
                "content": document.content,
                **document.metadata
            }
            
            # Extract keywords for better searchability
            keywords = self._extract_keywords(document.content)
            doc_data["keywords"] = keywords
            doc_data["created_at"] = firestore.SERVER_TIMESTAMP
            
            # Use the document ID or generate one
            doc_id = document.id or self._generate_doc_id(document.content)
            
            collection_ref.document(doc_id).set(doc_data)
            
            logger.info("Added document to Firestore", document_id=doc_id)
            
        except Exception as e:
            logger.error(
                "Failed to add document to Firestore",
                document_id=document.id,
                error=str(e),
                exc_info=True
            )
            raise

    def _extract_keywords(self, content: str) -> List[str]:
        """Extract keywords from content for better searchability"""
        # Simple keyword extraction - you might want to use more sophisticated methods
        words = re.findall(r'\b\w{4,}\b', content.lower())
        
        # Remove common stop words
        stop_words = {
            "this", "that", "with", "have", "will", "from", "they", "know", 
            "want", "been", "good", "much", "some", "time", "very", "when",
            "come", "here", "just", "like", "long", "make", "many", "over",
            "such", "take", "than", "them", "well", "were", "what"
        }
        
        keywords = [word for word in set(words) if word not in stop_words]
        return keywords[:50]  # Limit keywords

    def _generate_doc_id(self, content: str) -> str:
        """Generate a unique document ID based on content"""
        return hashlib.md5(content.encode()).hexdigest()[:16]

    async def get_collection_info(self) -> dict:
        await self._ensure_connection()
        
        try:
            collection_ref = self.client.collection(self.collection_name)
            count_query = collection_ref.count()
            count_result = count_query.get()
            count = count_result[0][0].value if count_result else 0
            
            return {
                "collection_name": self.collection_name,
                "document_count": count,
                "status": "connected"
            }
            
        except Exception as e:
            logger.error("Failed to get collection info", error=str(e), exc_info=True)
            return {
                "collection_name": self.collection_name,
                "status": "error",
                "error": str(e)
            }

    async def get_collections_info(self) -> dict:
        """Get information about collections in Firestore"""
        await self._ensure_connection()
        
        try:
            # Note: Firestore doesn't have a direct way to list all collections
            # This is a simplified version that only returns the current collection
            collection_info = await self.get_collection_info()
            
            return {
                "collections": [collection_info],
                "total_collections": 1
            }
            
        except Exception as e:
            logger.error("Failed to get collections info", error=str(e), exc_info=True)
            return {
                "error": str(e),
                "collections": []
            }

    async def get_documents(self, limit: int = 10, offset: int = 0) -> List[dict]:
        """Get documents from the collection with pagination"""
        await self._ensure_connection()
        
        try:
            collection_ref = self.client.collection(self.collection_name)
            
            # Firestore pagination using offset and limit
            query = collection_ref.order_by("created_at").limit(limit).offset(offset)
            docs = query.stream()
            
            documents = []
            for doc in docs:
                doc_data = doc.to_dict()
                documents.append({
                    "id": doc.id,
                    "content": doc_data.get("content", ""),
                    "metadata": {k: v for k, v in doc_data.items() if k != "content"}
                })
            
            return documents
            
        except Exception as e:
            logger.error("Failed to get documents", error=str(e), exc_info=True)
            return []