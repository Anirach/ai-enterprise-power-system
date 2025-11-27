"""
AI Power System - Knowledge Base Router
Handles document upload and management
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import uuid
import aiofiles
from datetime import datetime

router = APIRouter(prefix="/api/knowledge", tags=["Knowledge Base"])

# These will be injected from main.py
file_processor = None
web_crawler = None
embedding_service = None
retriever = None
upload_dir = "/app/uploads"

# In-memory document store (in production, use database)
documents_db: Dict[str, Dict[str, Any]] = {}


def set_services(fp, wc, es, ret, ud):
    global file_processor, web_crawler, embedding_service, retriever, upload_dir
    file_processor = fp
    web_crawler = wc
    embedding_service = es
    retriever = ret
    upload_dir = ud


class DocumentInfo(BaseModel):
    id: str
    filename: str
    file_type: str
    status: str
    chunks_count: int
    created_at: str
    metadata: Dict[str, Any] = {}


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


@router.post("/upload", response_model=DocumentInfo)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    metadata: Optional[str] = Form(None)
):
    """Upload a document to the knowledge base"""
    if not file_processor or not embedding_service or not retriever:
        raise HTTPException(status_code=503, detail="Services not initialized")
    
    # Validate file extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in file_processor.get_supported_extensions():
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Supported: {file_processor.get_supported_extensions()}"
        )
    
    # Generate unique ID and save file
    doc_id = str(uuid.uuid4())
    safe_filename = f"{doc_id}{ext}"
    file_path = os.path.join(upload_dir, safe_filename)
    
    # Ensure upload directory exists
    os.makedirs(upload_dir, exist_ok=True)
    
    # Save file
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    # Parse metadata
    meta = {}
    if metadata:
        import json
        try:
            meta = json.loads(metadata)
        except:
            pass
    
    # Store document info
    doc_info = {
        "id": doc_id,
        "filename": file.filename,
        "file_path": file_path,
        "file_type": ext,
        "status": "processing",
        "chunks_count": 0,
        "created_at": datetime.utcnow().isoformat(),
        "metadata": meta
    }
    documents_db[doc_id] = doc_info
    
    # Process in background
    background_tasks.add_task(process_document, doc_id, file_path, meta)
    
    return DocumentInfo(**doc_info)


async def process_document(doc_id: str, file_path: str, metadata: Dict[str, Any]):
    """Background task to process and index document"""
    try:
        # Process file
        result = await file_processor.process_file(file_path, metadata)
        chunks = result["chunks"]
        
        if chunks:
            # Generate embeddings
            embeddings = await embedding_service.embed_texts(chunks)
            
            # Store in vector database
            chunk_metadata = [
                {**metadata, "doc_id": doc_id, "chunk_index": i}
                for i in range(len(chunks))
            ]
            await retriever.add_documents(chunks, embeddings, chunk_metadata)
        
        # Update status
        documents_db[doc_id]["status"] = "completed"
        documents_db[doc_id]["chunks_count"] = len(chunks)
        
    except Exception as e:
        documents_db[doc_id]["status"] = "failed"
        documents_db[doc_id]["error"] = str(e)


@router.post("/crawl", response_model=CrawlResponse)
async def crawl_website(
    background_tasks: BackgroundTasks,
    request: CrawlRequest
):
    """Crawl a website and add to knowledge base"""
    if not web_crawler or not embedding_service or not retriever:
        raise HTTPException(status_code=503, detail="Services not initialized")
    
    doc_id = str(uuid.uuid4())
    
    # Store crawl info
    doc_info = {
        "id": doc_id,
        "filename": request.url,
        "file_path": "",
        "file_type": "web",
        "status": "crawling",
        "chunks_count": 0,
        "created_at": datetime.utcnow().isoformat(),
        "metadata": {"url": request.url}
    }
    documents_db[doc_id] = doc_info
    
    # Process in background
    background_tasks.add_task(
        process_crawl,
        doc_id,
        request.url,
        request.follow_links,
        request.max_depth
    )
    
    return CrawlResponse(
        id=doc_id,
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
        chunks = result["chunks"]
        
        if chunks:
            embeddings = await embedding_service.embed_texts(chunks)
            chunk_metadata = [
                {"doc_id": doc_id, "source": "web", "url": url, "chunk_index": i}
                for i in range(len(chunks))
            ]
            await retriever.add_documents(chunks, embeddings, chunk_metadata)
        
        documents_db[doc_id]["status"] = "completed"
        documents_db[doc_id]["chunks_count"] = len(chunks)
        documents_db[doc_id]["metadata"]["pages_crawled"] = result["pages_crawled"]
        
    except Exception as e:
        documents_db[doc_id]["status"] = "failed"
        documents_db[doc_id]["error"] = str(e)


@router.get("/documents", response_model=List[DocumentInfo])
async def list_documents():
    """List all documents in the knowledge base"""
    return [DocumentInfo(**doc) for doc in documents_db.values()]


@router.get("/documents/{doc_id}", response_model=DocumentInfo)
async def get_document(doc_id: str):
    """Get document details"""
    if doc_id not in documents_db:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentInfo(**documents_db[doc_id])


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document from the knowledge base"""
    if doc_id not in documents_db:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = documents_db[doc_id]
    
    # Delete from vector store
    if retriever:
        await retriever.delete_by_doc_id(doc_id)
    
    # Delete file if exists
    if doc.get("file_path") and os.path.exists(doc["file_path"]):
        os.remove(doc["file_path"])
    
    # Remove from database
    del documents_db[doc_id]
    
    return {"status": "deleted", "id": doc_id}


@router.get("/stats")
async def get_stats():
    """Get knowledge base statistics"""
    vector_stats = {}
    if retriever:
        vector_stats = await retriever.get_stats()
    
    return {
        "total_documents": len(documents_db),
        "by_status": {
            "completed": sum(1 for d in documents_db.values() if d["status"] == "completed"),
            "processing": sum(1 for d in documents_db.values() if d["status"] == "processing"),
            "failed": sum(1 for d in documents_db.values() if d["status"] == "failed")
        },
        "total_chunks": sum(d.get("chunks_count", 0) for d in documents_db.values()),
        "vector_store": vector_stats
    }


