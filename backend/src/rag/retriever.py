"""
AI Power System - Vector Retriever
Retrieves relevant documents from Qdrant vector database
"""
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue,
    PointsSelector, FilterSelector
)
import logging
import uuid

logger = logging.getLogger(__name__)


class VectorRetriever:
    """Service for storing and retrieving documents from Qdrant"""
    
    COLLECTION_NAME = "knowledge_base"
    
    def __init__(self, host: str, port: int, dimension: int = 768):
        self.client = QdrantClient(host=host, port=port)
        self.dimension = dimension
        self._ensure_collection()
    
    def _ensure_collection(self):
        """Ensure the collection exists"""
        try:
            collections = self.client.get_collections()
            exists = any(c.name == self.COLLECTION_NAME for c in collections.collections)
            
            if not exists:
                self.client.create_collection(
                    collection_name=self.COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=self.dimension,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created collection: {self.COLLECTION_NAME}")
        except Exception as e:
            logger.error(f"Failed to ensure collection: {e}")
    
    async def add_documents(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> List[str]:
        """Add documents with their embeddings to the vector store"""
        if metadatas is None:
            metadatas = [{} for _ in texts]
        
        ids = [str(uuid.uuid4()) for _ in texts]
        
        points = [
            PointStruct(
                id=idx,
                vector=embedding,
                payload={
                    "text": text,
                    "doc_id": doc_id,
                    **metadata
                }
            )
            for idx, (text, embedding, metadata, doc_id) in enumerate(
                zip(texts, embeddings, metadatas, ids),
                start=self._get_next_id()
            )
        ]
        
        self.client.upsert(
            collection_name=self.COLLECTION_NAME,
            points=points
        )
        
        logger.info(f"Added {len(texts)} documents to vector store")
        return ids
    
    def _get_next_id(self) -> int:
        """Get the next available ID"""
        try:
            info = self.client.get_collection(self.COLLECTION_NAME)
            return info.points_count or 0
        except Exception:
            return 0
    
    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar documents using query_points (newer API)"""
        search_filter = None
        if filter_dict:
            conditions = [
                FieldCondition(key=k, match=MatchValue(value=v))
                for k, v in filter_dict.items()
            ]
            search_filter = Filter(must=conditions)
        
        try:
            # Try newer API first (query_points)
            results = self.client.query_points(
                collection_name=self.COLLECTION_NAME,
                query=query_embedding,
                limit=top_k,
                query_filter=search_filter
            )
            
            return [
                {
                    "text": hit.payload.get("text", "") if hit.payload else "",
                    "score": hit.score,
                    "metadata": {k: v for k, v in (hit.payload or {}).items() if k != "text"}
                }
                for hit in results.points
            ]
        except AttributeError:
            # Fallback to older API (search)
            try:
                results = self.client.search(
                    collection_name=self.COLLECTION_NAME,
                    query_vector=query_embedding,
                    limit=top_k,
                    query_filter=search_filter
                )
                
                return [
                    {
                        "text": hit.payload.get("text", "") if hit.payload else "",
                        "score": hit.score,
                        "metadata": {k: v for k, v in (hit.payload or {}).items() if k != "text"}
                    }
                    for hit in results
                ]
            except Exception as e:
                logger.error(f"Search failed: {e}")
                return []
    
    async def delete_by_doc_id(self, doc_id: str) -> bool:
        """Delete all vectors associated with a document"""
        try:
            self.client.delete(
                collection_name=self.COLLECTION_NAME,
                points_selector=FilterSelector(
                    filter=Filter(
                        must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
                    )
                )
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        try:
            info = self.client.get_collection(self.COLLECTION_NAME)
            return {
                "collection": self.COLLECTION_NAME,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status.value if hasattr(info.status, 'value') else str(info.status)
            }
        except Exception as e:
            return {"error": str(e)}
