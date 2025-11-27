"""
AI Power System - Document Processor Worker
Handles document processing tasks from the queue
"""
import os
import asyncio
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Processes documents with parallel embedding generation.
    Designed to run as part of a worker pool.
    """
    
    def __init__(
        self,
        file_processor,
        embedding_service,
        retriever,
        minio_service,
        db_service
    ):
        self.file_processor = file_processor
        self.embedding_service = embedding_service
        self.retriever = retriever
        self.minio_service = minio_service
        self.db_service = db_service
    
    async def process_document(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a document from the task queue.
        
        Task format:
        {
            "id": "task-uuid",
            "doc_id": "document-uuid",
            "object_key": "minio-object-key",
            "filename": "original-filename.pdf",
            "metadata": {}
        }
        """
        doc_id = task["doc_id"]
        object_key = task["object_key"]
        filename = task["filename"]
        metadata = task.get("metadata", {})
        
        try:
            # Update progress: Starting
            await self.db_service.update_document(doc_id, progress=5)
            
            # Download file from MinIO
            file_data = self.minio_service.download_file(object_key)
            await self.db_service.update_document(doc_id, progress=10)
            
            # Save temporarily for processing
            temp_path = f"/tmp/{object_key}"
            with open(temp_path, "wb") as f:
                f.write(file_data)
            
            try:
                # Update progress: Processing with Docling
                await self.db_service.update_document(doc_id, progress=15)
                
                # Process file with Docling
                result = await self.file_processor.process_file(temp_path, metadata)
                chunks = result.get("chunks", [])
                content = result.get("content", "")
                doc_metadata = result.get("metadata", {})
                
                # Update progress: Parsing complete
                await self.db_service.update_document(doc_id, progress=40)
                
                # Calculate stats
                word_count = len(content.split()) if content else 0
                page_count = doc_metadata.get("page_count", 0)
                language = doc_metadata.get("language", "unknown")
                
                if chunks:
                    total_chunks = len(chunks)
                    
                    # Generate embeddings with TRUE parallel processing
                    await self.db_service.update_document(doc_id, progress=45)
                    
                    # Process embeddings in parallel batches
                    embeddings = await self._generate_embeddings_parallel(
                        chunks, 
                        doc_id,
                        batch_size=50,  # Larger batches
                        max_concurrent=20  # More concurrent requests
                    )
                    
                    # Store in vector database
                    await self.db_service.update_document(doc_id, progress=85)
                    chunk_metadata = [
                        {**metadata, "doc_id": doc_id, "chunk_index": i, "filename": filename}
                        for i in range(len(chunks))
                    ]
                    await self.retriever.add_documents(chunks, embeddings, chunk_metadata)
                    
                    # Store chunks in database
                    await self.db_service.update_document(doc_id, progress=90)
                    chunk_records = [
                        {"chunk_index": i, "content": chunk}
                        for i, chunk in enumerate(chunks)
                    ]
                    await self.db_service.create_chunks_batch(doc_id, chunk_records)
                
                # Update progress: Finalizing
                await self.db_service.update_document(doc_id, progress=95)
                
                # Update document status
                await self.db_service.update_document(
                    doc_id,
                    content=content,
                    chunks_count=len(chunks) if chunks else 0,
                    page_count=page_count,
                    word_count=word_count,
                    language=language,
                    status="completed",
                    progress=100
                )
                
                return {
                    "status": "completed",
                    "doc_id": doc_id,
                    "chunks": len(chunks) if chunks else 0,
                    "words": word_count
                }
                
            finally:
                # Clean up temp file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    
        except Exception as e:
            logger.error(f"Document processing failed for {doc_id}: {e}")
            await self.db_service.update_document(
                doc_id,
                status="failed",
                error_message=str(e),
                progress=0
            )
            raise
    
    async def _generate_embeddings_parallel(
        self,
        chunks: list,
        doc_id: str,
        batch_size: int = 50,
        max_concurrent: int = 20
    ) -> list:
        """
        Generate embeddings with true parallel processing.
        Uses semaphore to control concurrency.
        """
        total = len(chunks)
        embeddings = [None] * total
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def embed_single(idx: int, text: str):
            async with semaphore:
                try:
                    embedding = await self.embedding_service.embed_text(text)
                    return idx, embedding
                except Exception as e:
                    logger.error(f"Embedding failed for chunk {idx}: {e}")
                    return idx, [0.0] * self.embedding_service.dimension
        
        # Process all chunks in parallel with semaphore limiting
        tasks = [embed_single(i, chunk) for i, chunk in enumerate(chunks)]
        
        # Use asyncio.as_completed for progress updates
        completed = 0
        for coro in asyncio.as_completed(tasks):
            idx, embedding = await coro
            embeddings[idx] = embedding
            completed += 1
            
            # Update progress periodically (every 10%)
            if completed % max(1, total // 10) == 0:
                progress = 45 + int((completed / total) * 40)  # 45% to 85%
                await self.db_service.update_document(doc_id, progress=min(progress, 85))
        
        return embeddings


async def create_processor_from_app(app) -> DocumentProcessor:
    """Create a document processor from FastAPI app state"""
    from ..services import FileProcessor, MinIOService, DatabaseService
    from ..rag import EmbeddingService, VectorRetriever
    
    # Get services from app state or create new ones
    # This would need to be called with proper configuration
    pass

