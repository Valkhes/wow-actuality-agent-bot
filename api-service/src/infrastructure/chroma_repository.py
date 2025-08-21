import chromadb
from chromadb.config import Settings
import structlog
from typing import List, Optional
from ..domain.entities import VectorDocument
from ..domain.repositories import VectorRepository

logger = structlog.get_logger()


class ChromaVectorRepository(VectorRepository):
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
                    logger.info("Connected to existing ChromaDB collection", collection=self.collection_name)
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
                        metadata={"description": "World of Warcraft articles and news"}
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

    async def search_similar(self, query: str, k: int = 5) -> List[VectorDocument]:
        await self._ensure_connection()
        
        try:
            # Enhance query with synonyms and translations for better retrieval
            enhanced_queries = self._enhance_query(query)
            
            # Search with multiple query variants
            all_results = []
            for enhanced_query in enhanced_queries:
                results = self.collection.query(
                    query_texts=[enhanced_query],
                    n_results=k,
                    include=["documents", "metadatas", "distances"]
                )
                all_results.append((results, enhanced_query))
            
            # Combine and deduplicate results
            documents = []
            seen_ids = set()
            
            for results, used_query in all_results:
                if results["documents"] and results["documents"][0]:
                    for i, doc in enumerate(results["documents"][0]):
                        doc_id = results["ids"][0][i] if results["ids"] else f"doc_{i}"
                        
                        # Skip duplicates
                        if doc_id in seen_ids:
                            continue
                        seen_ids.add(doc_id)
                        
                        metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                        distance = results["distances"][0][i] if results["distances"] else None
                        
                        # Add similarity score (inverse of distance)
                        if distance is not None:
                            metadata["similarity_score"] = 1 / (1 + distance)
                        
                        metadata["matched_query"] = used_query
                        
                        documents.append(VectorDocument(
                            id=doc_id,
                            content=doc,
                            metadata=metadata
                        ))
            
            # Sort by similarity score and limit to k results
            documents.sort(key=lambda x: x.metadata.get("similarity_score", 0), reverse=True)
            documents = documents[:k]
            
            logger.info(
                "Retrieved similar documents from ChromaDB",
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
    
    def _enhance_query(self, query: str) -> List[str]:
        """Enhance query with variations for better retrieval"""
        enhanced = [query]  # Original query first
        
        query_lower = query.lower()
        
        # Add query variations without word boundaries
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
        
        return result[:3]  # Limit to 3 queries to avoid too many API calls

    async def add_document(self, document: VectorDocument) -> None:
        await self._ensure_connection()
        
        try:
            self.collection.add(
                documents=[document.content],
                metadatas=[document.metadata],
                ids=[document.id]
            )
            
            logger.info("Added document to ChromaDB", document_id=document.id)
            
        except Exception as e:
            logger.error(
                "Failed to add document to ChromaDB",
                document_id=document.id,
                error=str(e),
                exc_info=True
            )
            raise

    async def get_collection_info(self) -> dict:
        await self._ensure_connection()
        
        try:
            count = self.collection.count()
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
        """Get information about all collections in ChromaDB"""
        await self._ensure_connection()
        
        try:
            collections = self.client.list_collections()
            collections_data = []
            
            for collection in collections:
                try:
                    count = collection.count()
                    collections_data.append({
                        "name": collection.name,
                        "document_count": count,
                        "metadata": collection.metadata
                    })
                except Exception as e:
                    collections_data.append({
                        "name": collection.name,
                        "document_count": "error",
                        "error": str(e)
                    })
            
            return {
                "collections": collections_data,
                "total_collections": len(collections_data)
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
            # Get all document IDs first to handle pagination
            result = self.collection.get(
                limit=limit,
                offset=offset,
                include=["documents", "metadatas", "ids"]
            )
            
            documents = []
            for i, doc_id in enumerate(result["ids"]):
                documents.append({
                    "id": doc_id,
                    "content": result["documents"][i] if i < len(result["documents"]) else "",
                    "metadata": result["metadatas"][i] if i < len(result["metadatas"]) else {}
                })
            
            return documents
            
        except Exception as e:
            logger.error("Failed to get documents", error=str(e), exc_info=True)
            return []