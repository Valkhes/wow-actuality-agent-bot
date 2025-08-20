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
                except Exception:
                    self.collection = self.client.create_collection(
                        name=self.collection_name,
                        metadata={"description": "World of Warcraft articles and news"}
                    )
                    logger.info("Created new ChromaDB collection", collection=self.collection_name)
                    
            except Exception as e:
                logger.error("Failed to connect to ChromaDB", error=str(e), exc_info=True)
                raise ConnectionError(f"Cannot connect to ChromaDB: {str(e)}")

    async def search_similar(self, query: str, k: int = 5) -> List[VectorDocument]:
        await self._ensure_connection()
        
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=k,
                include=["documents", "metadatas", "distances"]
            )
            
            documents = []
            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                    distance = results["distances"][0][i] if results["distances"] else None
                    
                    # Add similarity score (inverse of distance)
                    if distance is not None:
                        metadata["similarity_score"] = 1 / (1 + distance)
                    
                    documents.append(VectorDocument(
                        id=results["ids"][0][i] if results["ids"] else f"doc_{i}",
                        content=doc,
                        metadata=metadata
                    ))
            
            logger.info(
                "Retrieved similar documents from ChromaDB",
                query_length=len(query),
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