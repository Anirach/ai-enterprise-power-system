"""
AI Power System - PostgreSQL Database Service
Handles async database operations for documents and chunks
"""
import os
import uuid
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

import asyncpg

logger = logging.getLogger(__name__)


class DatabaseService:
    """Async PostgreSQL service for document management"""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or os.getenv(
            "DATABASE_URL",
            "postgresql://aipower:aipower@postgres:5432/aipower_db"
        )
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        """Create connection pool"""
        if self.pool is None:
            try:
                async def init_connection(conn):
                    # Register JSON codec for JSONB columns
                    await conn.set_type_codec(
                        'jsonb',
                        encoder=json.dumps,
                        decoder=json.loads,
                        schema='pg_catalog'
                    )
                    await conn.set_type_codec(
                        'json',
                        encoder=json.dumps,
                        decoder=json.loads,
                        schema='pg_catalog'
                    )
                
                self.pool = await asyncpg.create_pool(
                    self.database_url,
                    min_size=2,
                    max_size=10,
                    init=init_connection
                )
                logger.info("Database connection pool created")
            except Exception as e:
                logger.error(f"Failed to create database pool: {e}")
                raise
    
    async def disconnect(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Database connection pool closed")
    
    async def health_check(self) -> bool:
        """Check database connectivity"""
        try:
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception:
            return False
    
    # ==================== DOCUMENT OPERATIONS ====================
    
    async def create_document(
        self,
        name: str,
        file_type: str,
        content_type: str = None,
        file_size: int = 0,
        minio_bucket: str = None,
        minio_object_key: str = None,
        content: str = None,
        page_count: int = 0,
        word_count: int = 0,
        language: str = "unknown",
        tags: List[str] = None,
        metadata: Dict[str, Any] = None,
        status: str = "pending"
    ) -> Dict[str, Any]:
        """Create a new document record"""
        doc_id = uuid.uuid4()
        
        query = """
            INSERT INTO documents (
                id, name, file_type, content_type, file_size,
                minio_bucket, minio_object_key, content,
                page_count, word_count, language, tags, metadata, status
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14
            )
            RETURNING *
        """
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                query,
                doc_id,
                name,
                file_type,
                content_type,
                file_size,
                minio_bucket,
                minio_object_key,
                content,
                page_count,
                word_count,
                language,
                tags or [],
                metadata or {},
                status
            )
        
        return self._row_to_dict(row)
    
    async def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get a document by ID"""
        query = "SELECT * FROM documents WHERE id = $1"
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, uuid.UUID(doc_id))
        
        return self._row_to_dict(row) if row else None
    
    async def get_documents(
        self,
        status: str = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get all documents with optional filtering"""
        if status:
            query = """
                SELECT * FROM documents 
                WHERE status = $1 
                ORDER BY created_at DESC 
                LIMIT $2 OFFSET $3
            """
            params = (status, limit, offset)
        else:
            query = """
                SELECT * FROM documents 
                ORDER BY created_at DESC 
                LIMIT $1 OFFSET $2
            """
            params = (limit, offset)
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        
        return [self._row_to_dict(row) for row in rows]
    
    async def get_document_content(self, doc_id: str) -> Optional[str]:
        """Get only the content of a document"""
        query = "SELECT content FROM documents WHERE id = $1"
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, uuid.UUID(doc_id))
        
        return row["content"] if row else None
    
    async def update_document(
        self,
        doc_id: str,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Update a document"""
        # Build dynamic update query
        set_clauses = []
        values = []
        param_idx = 1
        
        allowed_fields = [
            "name", "file_type", "content_type", "file_size",
            "minio_bucket", "minio_object_key", "content",
            "chunks_count", "status", "error_message",
            "page_count", "word_count", "language", "tags", "metadata", "progress"
        ]
        
        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                set_clauses.append(f"{field} = ${param_idx}")
                values.append(value)
                param_idx += 1
        
        if not set_clauses:
            return await self.get_document(doc_id)
        
        values.append(uuid.UUID(doc_id))
        query = f"""
            UPDATE documents 
            SET {', '.join(set_clauses)}
            WHERE id = ${param_idx}
            RETURNING *
        """
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *values)
        
        return self._row_to_dict(row) if row else None
    
    async def delete_document(self, doc_id: str) -> bool:
        """Delete a document and its chunks"""
        query = "DELETE FROM documents WHERE id = $1 RETURNING id"
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, uuid.UUID(doc_id))
        
        return row is not None
    
    async def get_documents_count(self, status: str = None) -> int:
        """Get document count"""
        if status:
            query = "SELECT COUNT(*) FROM documents WHERE status = $1"
            params = (status,)
        else:
            query = "SELECT COUNT(*) FROM documents"
            params = ()
        
        async with self.pool.acquire() as conn:
            count = await conn.fetchval(query, *params)
        
        return count
    
    async def get_documents_summary(self) -> Dict[str, Any]:
        """Get summary of all documents for chat context"""
        query = """
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE status = 'completed') as completed,
                COUNT(*) FILTER (WHERE status = 'processing') as processing,
                COUNT(*) FILTER (WHERE status = 'failed') as failed,
                COALESCE(SUM(chunks_count), 0) as total_chunks,
                COALESCE(SUM(word_count), 0) as total_words
            FROM documents
        """
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query)
        
        return dict(row) if row else {}
    
    async def get_document_names(self) -> List[Dict[str, Any]]:
        """Get list of document names and basic info"""
        query = """
            SELECT id, name, file_type, status, page_count, word_count, created_at
            FROM documents
            WHERE status = 'completed'
            ORDER BY created_at DESC
        """
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query)
        
        return [dict(row) for row in rows]
    
    async def update_document_tags(
        self,
        doc_id: str,
        tags: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Update document tags"""
        return await self.update_document(doc_id, tags=tags)
    
    # ==================== CHUNK OPERATIONS ====================
    
    async def create_chunk(
        self,
        document_id: str,
        chunk_index: int,
        content: str,
        embedding_id: str = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Create a chunk record"""
        chunk_id = uuid.uuid4()
        
        query = """
            INSERT INTO chunks (id, document_id, chunk_index, content, embedding_id, metadata)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
        """
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                query,
                chunk_id,
                uuid.UUID(document_id),
                chunk_index,
                content,
                embedding_id,
                metadata or {}
            )
        
        return self._row_to_dict(row)
    
    async def create_chunks_batch(
        self,
        document_id: str,
        chunks: List[Dict[str, Any]]
    ) -> int:
        """Create multiple chunks in a batch"""
        query = """
            INSERT INTO chunks (id, document_id, chunk_index, content, embedding_id, metadata)
            VALUES ($1, $2, $3, $4, $5, $6)
        """
        
        records = [
            (
                uuid.uuid4(),
                uuid.UUID(document_id),
                chunk["chunk_index"],
                chunk["content"],
                chunk.get("embedding_id"),
                chunk.get("metadata", {})
            )
            for chunk in chunks
        ]
        
        async with self.pool.acquire() as conn:
            await conn.executemany(query, records)
        
        return len(records)
    
    async def get_chunks_by_document(
        self,
        document_id: str
    ) -> List[Dict[str, Any]]:
        """Get all chunks for a document"""
        query = """
            SELECT * FROM chunks 
            WHERE document_id = $1 
            ORDER BY chunk_index
        """
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, uuid.UUID(document_id))
        
        return [self._row_to_dict(row) for row in rows]
    
    async def delete_chunks_by_document(self, document_id: str) -> int:
        """Delete all chunks for a document"""
        query = "DELETE FROM chunks WHERE document_id = $1"
        
        async with self.pool.acquire() as conn:
            result = await conn.execute(query, uuid.UUID(document_id))
        
        # Parse the result to get count (e.g., "DELETE 5")
        count = int(result.split()[-1]) if result else 0
        return count
    
    # ==================== STATS ====================
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get overall statistics"""
        docs_query = """
            SELECT 
                COUNT(*) as total_documents,
                COUNT(*) FILTER (WHERE status = 'completed') as completed,
                COUNT(*) FILTER (WHERE status = 'processing') as processing,
                COUNT(*) FILTER (WHERE status = 'failed') as failed,
                COALESCE(SUM(chunks_count), 0) as total_chunks,
                COALESCE(SUM(file_size), 0) as total_size
            FROM documents
        """
        
        async with self.pool.acquire() as conn:
            doc_stats = await conn.fetchrow(docs_query)
        
        return {
            "documents": dict(doc_stats) if doc_stats else {},
        }
    
    # ==================== HELPERS ====================
    
    def _row_to_dict(self, row: asyncpg.Record) -> Dict[str, Any]:
        """Convert database row to dictionary"""
        if row is None:
            return None
        
        result = dict(row)
        
        # Convert UUID to string
        for key, value in result.items():
            if isinstance(value, uuid.UUID):
                result[key] = str(value)
            elif isinstance(value, datetime):
                result[key] = value.isoformat()
        
        return result

