"""
AI Power System - Knowledge Base Router
Handles document upload, storage (MinIO), and management (PostgreSQL)
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import io
import uuid
import mimetypes
from datetime import datetime

router = APIRouter(prefix="/api/knowledge", tags=["Knowledge Base"])

# Services - will be injected from main.py
file_processor = None
web_crawler = None
embedding_service = None
retriever = None
minio_service = None
db_service = None
worker_pool = None  # Worker pool for parallel processing


def set_services(fp, wc, es, ret, minio, db, wp=None):
    """Set service instances"""
    global file_processor, web_crawler, embedding_service, retriever, minio_service, db_service, worker_pool
    file_processor = fp
    web_crawler = wc
    embedding_service = es
    retriever = ret
    minio_service = minio
    db_service = db
    worker_pool = wp


# ==================== MODELS ====================

class DocumentInfo(BaseModel):
    id: str
    name: str
    file_type: str
    content_type: Optional[str] = None
    file_size: int = 0
    status: str
    chunks_count: int = 0
    page_count: int = 0
    word_count: int = 0
    language: str = "unknown"
    tags: List[str] = []
    created_at: str
    metadata: Dict[str, Any] = {}
    progress: int = 0  # Processing progress 0-100


class DocumentContent(BaseModel):
    id: str
    name: str
    content: Optional[str] = None
    chunks_count: int = 0


class CrawlRequest(BaseModel):
    url: str
    follow_links: bool = False
    max_depth: int = 1


class CrawlResponse(BaseModel):
    id: str
    url: str
    pages_crawled: int
    chunks_count: int
    status: str


class UpdateTagsRequest(BaseModel):
    tags: List[str]


class StatsResponse(BaseModel):
    total_documents: int
    by_status: Dict[str, int]
    total_chunks: int
    total_size: int
    vector_store: Dict[str, Any]


# ==================== UPLOAD ENDPOINT ====================

@router.post("/upload", response_model=DocumentInfo)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    tags: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None)
):
    """Upload a document to MinIO and process it"""
    if not all([file_processor, embedding_service, retriever, minio_service, db_service]):
        raise HTTPException(status_code=503, detail="Services not initialized")
    
    # Validate file extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in file_processor.get_supported_extensions():
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Supported: {file_processor.get_supported_extensions()}"
        )
    
    # Read file content
    file_content = await file.read()
    file_size = len(file_content)
    
    # Detect content type
    content_type = file.content_type or mimetypes.guess_type(file.filename)[0] or "application/octet-stream"
    
    # Upload to MinIO
    minio_result = minio_service.upload_bytes(
        data=file_content,
        original_filename=file.filename,
        content_type=content_type
    )
    
    # Parse tags
    tag_list = []
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    
    # Parse metadata
    meta = {}
    if metadata:
        import json
        try:
            meta = json.loads(metadata)
        except:
            pass
    
    # Create document record in database
    doc = await db_service.create_document(
        name=file.filename,
        file_type=ext,
        content_type=content_type,
        file_size=file_size,
        minio_bucket=minio_result["bucket"],
        minio_object_key=minio_result["object_key"],
        tags=tag_list,
        metadata=meta,
        status="processing"
    )
    
    # Queue for parallel processing via worker pool
    if worker_pool:
        await worker_pool.enqueue_document({
            "doc_id": doc["id"],
            "object_key": minio_result["object_key"],
            "filename": file.filename,
            "metadata": meta
        })
    else:
        # Fallback to background task if worker pool not available
        background_tasks.add_task(
            process_document,
            doc["id"],
            minio_result["object_key"],
            file.filename,
            meta
        )
    
    return DocumentInfo(
        id=doc["id"],
        name=doc["name"],
        file_type=doc["file_type"],
        content_type=doc["content_type"],
        file_size=doc["file_size"],
        status=doc["status"],
        chunks_count=doc["chunks_count"],
        page_count=doc["page_count"],
        word_count=doc["word_count"],
        language=doc["language"],
        tags=doc["tags"] or [],
        created_at=doc["created_at"],
        metadata=doc["metadata"] or {},
        progress=doc.get("progress", 0)
    )


async def process_document(
    doc_id: str,
    object_key: str,
    filename: str,
    metadata: Dict[str, Any]
):
    """Background task to process and index document"""
    try:
        # Update progress: Starting
        await db_service.update_document(doc_id, progress=5)
        
        # Download file from MinIO
        file_data = minio_service.download_file(object_key)
        await db_service.update_document(doc_id, progress=10)
        
        # Save temporarily for processing
        temp_path = f"/tmp/{object_key}"
        with open(temp_path, "wb") as f:
            f.write(file_data)
        
        try:
            # Update progress: Processing with Docling
            await db_service.update_document(doc_id, progress=15)
            
            # Process file with Docling
            result = await file_processor.process_file(temp_path, metadata)
            chunks = result.get("chunks", [])
            content = result.get("content", "")
            doc_metadata = result.get("metadata", {})
            
            # Update progress: Parsing complete
            await db_service.update_document(doc_id, progress=40)
            
            # Calculate word count
            word_count = len(content.split()) if content else 0
            page_count = doc_metadata.get("page_count", 0)
            language = doc_metadata.get("language", "unknown")
            
            if chunks:
                total_chunks = len(chunks)
                
                # Generate embeddings with parallel processing and progress updates
                await db_service.update_document(doc_id, progress=50)
                
                # Progress callback for real-time updates
                async def embedding_progress(processed: int, total: int):
                    # Map embedding progress (0-100%) to document progress (50-80%)
                    progress = 50 + int((processed / total) * 30)
                    await db_service.update_document(doc_id, progress=min(progress, 80))
                
                # Use optimized parallel embedding with larger batches
                # Batch size of 20+ for better throughput with concurrent processing
                embeddings = await embedding_service.embed_texts(
                    chunks, 
                    batch_size=25,  # Larger batches with parallel processing
                    progress_callback=embedding_progress
                )
                
                # Store in vector database
                await db_service.update_document(doc_id, progress=85)
                chunk_metadata = [
                    {**metadata, "doc_id": doc_id, "chunk_index": i, "filename": filename}
                    for i in range(len(chunks))
                ]
                await retriever.add_documents(chunks, embeddings, chunk_metadata)
                
                # Store chunks in database
                await db_service.update_document(doc_id, progress=90)
                chunk_records = [
                    {"chunk_index": i, "content": chunk}
                    for i, chunk in enumerate(chunks)
                ]
                await db_service.create_chunks_batch(doc_id, chunk_records)
            
            # Update progress: Finalizing
            await db_service.update_document(doc_id, progress=95)
            
            # Update document status
            await db_service.update_document(
                doc_id,
                content=content,
                chunks_count=len(chunks),
                page_count=page_count,
                word_count=word_count,
                language=language,
                status="completed",
                progress=100
            )
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    except Exception as e:
        await db_service.update_document(
            doc_id,
            status="failed",
            error_message=str(e),
            progress=0
        )


# ==================== CRAWL ENDPOINT ====================

@router.post("/crawl", response_model=CrawlResponse)
async def crawl_website(
    background_tasks: BackgroundTasks,
    request: CrawlRequest
):
    """Crawl a website and add to knowledge base"""
    if not all([web_crawler, embedding_service, retriever, db_service]):
        raise HTTPException(status_code=503, detail="Services not initialized")
    
    # Create document record
    doc = await db_service.create_document(
        name=request.url,
        file_type="web",
        content_type="text/html",
        metadata={"url": request.url},
        status="crawling"
    )
    
    # Process in background
    background_tasks.add_task(
        process_crawl,
        doc["id"],
        request.url,
        request.follow_links,
        request.max_depth
    )
    
    return CrawlResponse(
        id=doc["id"],
        url=request.url,
        pages_crawled=0,
        chunks_count=0,
        status="crawling"
    )


async def process_crawl(
    doc_id: str,
    url: str,
    follow_links: bool,
    max_depth: int
):
    """Background task to crawl and index website"""
    try:
        result = await web_crawler.crawl_url(url, follow_links, max_depth)
        chunks = result.get("chunks", [])
        content = result.get("content", "")
        
        word_count = len(content.split()) if content else 0
        
        if chunks:
            embeddings = await embedding_service.embed_texts(chunks)
            chunk_metadata = [
                {"doc_id": doc_id, "source": "web", "url": url, "chunk_index": i}
                for i in range(len(chunks))
            ]
            await retriever.add_documents(chunks, embeddings, chunk_metadata)
            
            chunk_records = [
                {"chunk_index": i, "content": chunk}
                for i, chunk in enumerate(chunks)
            ]
            await db_service.create_chunks_batch(doc_id, chunk_records)
        
        await db_service.update_document(
            doc_id,
            content=content,
            chunks_count=len(chunks),
            word_count=word_count,
            status="completed",
            metadata={"url": url, "pages_crawled": result.get("pages_crawled", 1)}
        )
        
    except Exception as e:
        await db_service.update_document(
            doc_id,
            status="failed",
            error_message=str(e)
        )


# ==================== LIST & GET ENDPOINTS ====================

@router.get("/documents", response_model=List[DocumentInfo])
async def list_documents(
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """List all documents in the knowledge base"""
    if not db_service:
        raise HTTPException(status_code=503, detail="Database service not initialized")
    
    docs = await db_service.get_documents(status=status, limit=limit, offset=offset)
    
    return [
        DocumentInfo(
            id=doc["id"],
            name=doc["name"],
            file_type=doc["file_type"],
            content_type=doc.get("content_type"),
            file_size=doc.get("file_size", 0),
            status=doc["status"],
            chunks_count=doc.get("chunks_count", 0),
            page_count=doc.get("page_count", 0),
            word_count=doc.get("word_count", 0),
            language=doc.get("language", "unknown"),
            tags=doc.get("tags") or [],
            created_at=doc["created_at"],
            metadata=doc.get("metadata") or {},
            progress=doc.get("progress", 100 if doc["status"] == "completed" else 0)
        )
        for doc in docs
    ]


@router.get("/documents/{doc_id}", response_model=DocumentInfo)
async def get_document(doc_id: str):
    """Get document details"""
    if not db_service:
        raise HTTPException(status_code=503, detail="Database service not initialized")
    
    doc = await db_service.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return DocumentInfo(
        id=doc["id"],
        name=doc["name"],
        file_type=doc["file_type"],
        content_type=doc.get("content_type"),
        file_size=doc.get("file_size", 0),
        status=doc["status"],
        chunks_count=doc.get("chunks_count", 0),
        page_count=doc.get("page_count", 0),
        word_count=doc.get("word_count", 0),
        language=doc.get("language", "unknown"),
        tags=doc.get("tags") or [],
        created_at=doc["created_at"],
        metadata=doc.get("metadata") or {},
        progress=doc.get("progress", 100 if doc["status"] == "completed" else 0)
    )


@router.get("/documents/{doc_id}/content", response_model=DocumentContent)
async def get_document_content(doc_id: str):
    """Get document text content"""
    if not db_service:
        raise HTTPException(status_code=503, detail="Database service not initialized")
    
    doc = await db_service.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return DocumentContent(
        id=doc["id"],
        name=doc["name"],
        content=doc.get("content"),
        chunks_count=doc.get("chunks_count", 0)
    )


@router.get("/documents/{doc_id}/download")
async def download_document(doc_id: str):
    """Download original document from MinIO"""
    if not db_service or not minio_service:
        raise HTTPException(status_code=503, detail="Services not initialized")
    
    doc = await db_service.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not doc.get("minio_object_key"):
        raise HTTPException(status_code=404, detail="File not available for download")
    
    # Download from MinIO
    file_data = minio_service.download_file(doc["minio_object_key"])
    
    return Response(
        content=file_data,
        media_type=doc.get("content_type", "application/octet-stream"),
        headers={
            "Content-Disposition": f'attachment; filename="{doc["name"]}"'
        }
    )


# ==================== UPDATE & DELETE ENDPOINTS ====================

@router.patch("/documents/{doc_id}/tags", response_model=DocumentInfo)
async def update_document_tags(doc_id: str, request: UpdateTagsRequest):
    """Update document tags"""
    if not db_service:
        raise HTTPException(status_code=503, detail="Database service not initialized")
    
    doc = await db_service.update_document_tags(doc_id, request.tags)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return DocumentInfo(
        id=doc["id"],
        name=doc["name"],
        file_type=doc["file_type"],
        content_type=doc.get("content_type"),
        file_size=doc.get("file_size", 0),
        status=doc["status"],
        chunks_count=doc.get("chunks_count", 0),
        page_count=doc.get("page_count", 0),
        word_count=doc.get("word_count", 0),
        language=doc.get("language", "unknown"),
        tags=doc.get("tags") or [],
        created_at=doc["created_at"],
        metadata=doc.get("metadata") or {},
        progress=doc.get("progress", 100 if doc["status"] == "completed" else 0)
    )


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document from MinIO, PostgreSQL, and Qdrant"""
    if not db_service:
        raise HTTPException(status_code=503, detail="Database service not initialized")
    
    # Get document info first
    doc = await db_service.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    errors = []
    
    # 1. Delete from MinIO
    if minio_service and doc.get("minio_object_key"):
        try:
            minio_service.delete_file(doc["minio_object_key"])
        except Exception as e:
            errors.append(f"MinIO: {str(e)}")
    
    # 2. Delete from Qdrant (vector store)
    if retriever:
        try:
            await retriever.delete_by_doc_id(doc_id)
        except Exception as e:
            errors.append(f"Qdrant: {str(e)}")
    
    # 3. Delete chunks from PostgreSQL
    try:
        await db_service.delete_chunks_by_document(doc_id)
    except Exception as e:
        errors.append(f"Chunks: {str(e)}")
    
    # 4. Delete document from PostgreSQL
    deleted = await db_service.delete_document(doc_id)
    if not deleted:
        errors.append("Failed to delete document record")
    
    return {
        "status": "deleted" if not errors else "partial",
        "id": doc_id,
        "errors": errors if errors else None
    }


@router.post("/documents/{doc_id}/reprocess")
async def reprocess_document(doc_id: str):
    """Re-queue a document for processing"""
    if not db_service:
        raise HTTPException(status_code=503, detail="Database service not initialized")
    
    doc = await db_service.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Only allow reprocessing of pending, failed, or stuck processing documents
    if doc["status"] not in ["pending", "failed", "processing"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot reprocess document with status '{doc['status']}'. Only pending, failed, or processing documents can be reprocessed."
        )
    
    # Reset document status
    await db_service.update_document(doc_id, status="processing", progress=0, error_message=None)
    
    # Delete existing chunks if any
    try:
        await db_service.delete_chunks_by_document(doc_id)
    except:
        pass
    
    # Delete from vector store if any
    if retriever:
        try:
            await retriever.delete_by_doc_id(doc_id)
        except:
            pass
    
    # Queue for processing
    if worker_pool:
        await worker_pool.enqueue_document({
            "doc_id": doc_id,
            "object_key": doc.get("minio_object_key"),
            "filename": doc["name"],
            "metadata": doc.get("metadata", {})
        })
        return {"status": "queued", "id": doc_id, "message": "Document queued for reprocessing"}
    else:
        raise HTTPException(status_code=503, detail="Worker pool not available")


@router.post("/reprocess-all-pending")
async def reprocess_all_pending():
    """Re-queue all pending or failed documents for processing"""
    if not db_service:
        raise HTTPException(status_code=503, detail="Database service not initialized")
    
    if not worker_pool:
        raise HTTPException(status_code=503, detail="Worker pool not available")
    
    # Get all pending and failed documents
    pending_docs = await db_service.get_documents(status="pending", limit=1000)
    failed_docs = await db_service.get_documents(status="failed", limit=1000)
    
    queued_count = 0
    
    for doc in pending_docs + failed_docs:
        doc_id = doc["id"]
        
        # Reset document status
        await db_service.update_document(doc_id, status="processing", progress=0, error_message=None)
        
        # Delete existing chunks if any
        try:
            await db_service.delete_chunks_by_document(doc_id)
        except:
            pass
        
        # Delete from vector store if any
        if retriever:
            try:
                await retriever.delete_by_doc_id(doc_id)
            except:
                pass
        
        # Queue for processing
        await worker_pool.enqueue_document({
            "doc_id": doc_id,
            "object_key": doc.get("minio_object_key"),
            "filename": doc["name"],
            "metadata": doc.get("metadata", {})
        })
        queued_count += 1
    
    return {
        "status": "success",
        "queued_count": queued_count,
        "message": f"Queued {queued_count} documents for reprocessing"
    }


@router.delete("/clear-all")
async def clear_all_knowledge():
    """Clear all documents from MinIO, PostgreSQL, and Qdrant"""
    if not db_service:
        raise HTTPException(status_code=503, detail="Database service not initialized")
    
    # Get all documents
    docs = await db_service.get_documents(limit=10000)
    
    deleted_count = 0
    errors = []
    
    for doc in docs:
        doc_id = doc["id"]
        try:
            # Delete from MinIO
            if minio_service and doc.get("minio_object_key"):
                try:
                    minio_service.delete_file(doc["minio_object_key"])
                except Exception as e:
                    errors.append(f"MinIO {doc['name']}: {str(e)}")
            
            # Delete from Qdrant
            if retriever:
                try:
                    await retriever.delete_by_doc_id(doc_id)
                except Exception as e:
                    errors.append(f"Qdrant {doc['name']}: {str(e)}")
            
            # Delete chunks from PostgreSQL
            try:
                await db_service.delete_chunks_by_document(doc_id)
            except Exception as e:
                errors.append(f"Chunks {doc['name']}: {str(e)}")
            
            # Delete document from PostgreSQL
            await db_service.delete_document(doc_id)
            deleted_count += 1
            
        except Exception as e:
            errors.append(f"Document {doc['name']}: {str(e)}")
    
    # Also clear all vectors from Qdrant collection
    if retriever:
        try:
            await retriever.clear_collection()
        except Exception as e:
            errors.append(f"Clear Qdrant collection: {str(e)}")
    
    return {
        "status": "success" if not errors else "partial",
        "deleted_count": deleted_count,
        "errors": errors[:10] if errors else None  # Limit errors to prevent large response
    }


# ==================== STATS ENDPOINT ====================

@router.get("/stats")
async def get_stats():
    """Get knowledge base statistics"""
    if not db_service:
        raise HTTPException(status_code=503, detail="Database service not initialized")
    
    db_stats = await db_service.get_stats()
    doc_stats = db_stats.get("documents", {})
    
    vector_stats = {}
    if retriever:
        try:
            vector_stats = await retriever.get_stats()
        except:
            pass
    
    return {
        "total_documents": doc_stats.get("total_documents", 0),
        "by_status": {
            "completed": doc_stats.get("completed", 0),
            "processing": doc_stats.get("processing", 0),
            "failed": doc_stats.get("failed", 0)
        },
        "total_chunks": doc_stats.get("total_chunks", 0),
        "total_size": doc_stats.get("total_size", 0),
        "vector_store": vector_stats
    }


# ==================== WORKER STATS ====================

@router.get("/workers/stats")
async def get_worker_stats():
    """Get worker pool statistics"""
    if not worker_pool:
        return {
            "status": "disabled",
            "message": "Worker pool not initialized"
        }
    
    stats = await worker_pool.get_stats()
    return {
        "status": "active",
        **stats
    }


# ==================== DOCUMENT LIST FOR CHAT ====================

@router.get("/documents/list/names")
async def get_document_names():
    """Get list of document names for chat context"""
    if not db_service:
        raise HTTPException(status_code=503, detail="Database service not initialized")
    
    docs = await db_service.get_document_names()
    summary = await db_service.get_documents_summary()
    
    return {
        "total": summary.get("total", 0),
        "completed": summary.get("completed", 0),
        "total_words": summary.get("total_words", 0),
        "documents": [
            {
                "name": doc["name"],
                "type": doc["file_type"],
                "pages": doc.get("page_count", 0),
                "words": doc.get("word_count", 0)
            }
            for doc in docs
        ]
    }
