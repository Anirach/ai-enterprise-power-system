"""
AI Power System - Main Application
=====================================
FastAPI application with RAG pipeline, file processing, and web crawling.
Connects to Ollama, Qdrant, PostgreSQL, MinIO, and Redis.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import httpx
import redis
import logging
import os
from datetime import datetime

from .config import get_settings
from .rag import EmbeddingService, VectorRetriever, RAGPipeline
from .rag.embeddings import LocalEmbeddingService
from .services import FileProcessor, WebCrawler
from .services.minio_service import MinIOService
from .services.database import DatabaseService
from .routers import chat, knowledge, admin
from .workers import WorkerPool
from .workers.document_processor import DocumentProcessor

# ============================================================
# CONFIGURATION
# ============================================================

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.app_log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================
# GLOBAL SERVICES
# ============================================================

embedding_service: EmbeddingService = None
retriever: VectorRetriever = None
rag_pipeline: RAGPipeline = None
file_processor: FileProcessor = None
web_crawler: WebCrawler = None
redis_client: redis.Redis = None
minio_service: MinIOService = None
db_service: DatabaseService = None
worker_pool: WorkerPool = None
document_processor: DocumentProcessor = None


# ============================================================
# LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown"""
    global embedding_service, retriever, rag_pipeline, file_processor, web_crawler
    global redis_client, minio_service, db_service, worker_pool, document_processor
    
    logger.info("🚀 Starting AI Power System...")
    
    # Initialize Database Service
    try:
        db_service = DatabaseService(settings.database_url)
        await db_service.connect()
        logger.info("✅ Database service connected to PostgreSQL")
    except Exception as e:
        logger.warning(f"⚠️ PostgreSQL connection failed: {e}")
        db_service = None
    
    # Initialize MinIO Service
    try:
        minio_service = MinIOService(
            endpoint=os.getenv("MINIO_ENDPOINT", "minio:9000"),
            access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
            secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin123"),
            bucket_name=os.getenv("MINIO_BUCKET", "documents")
        )
        logger.info("✅ MinIO service initialized")
    except Exception as e:
        logger.warning(f"⚠️ MinIO connection failed: {e}")
        minio_service = None
    
    # Initialize FAST LOCAL embedding service using sentence-transformers
    # This is 100x faster than Ollama for batch embeddings!
    use_local_embeddings = os.getenv("USE_LOCAL_EMBEDDINGS", "true").lower() == "true"
    
    if use_local_embeddings:
        embedding_service = LocalEmbeddingService(
            model_name="all-MiniLM-L6-v2",  # Fast & high quality (384 dim)
            device="cpu",
            cache_size=5000
        )
        logger.info("✅ Using FAST LOCAL embedding service (sentence-transformers)")
        embedding_dimension = 384  # MiniLM dimension
    else:
        embedding_service = EmbeddingService(
            base_url=settings.ollama_base_url,
            model=settings.ollama_embedding_model,
            max_concurrent=50,
            timeout=180.0,
            cache_size=5000
        )
        logger.info(f"✅ Using Ollama embedding service (model: {settings.ollama_embedding_model})")
        embedding_dimension = 768  # nomic-embed-text dimension
    
    # Warm up the embedding model
    try:
        await embedding_service.embed_text("warmup test")
        logger.info("✅ Embedding model warmed up")
    except Exception as e:
        logger.warning(f"⚠️ Embedding warmup failed (will warm on first use): {e}")
    
    # Initialize vector retriever with matching dimension
    try:
        retriever = VectorRetriever(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            dimension=embedding_dimension  # Use correct dimension for embedding model
        )
        logger.info(f"✅ Vector retriever connected to Qdrant (dimension={embedding_dimension})")
    except Exception as e:
        logger.warning(f"⚠️ Qdrant connection failed: {e}")
        retriever = None
    
    # Initialize RAG pipeline with database service for document awareness
    if retriever:
        rag_pipeline = RAGPipeline(
            embedding_service=embedding_service,
            retriever=retriever,
            ollama_base_url=settings.ollama_base_url,
            default_model=settings.ollama_default_model,
            db_service=db_service  # Pass db_service for document queries
        )
        logger.info("✅ RAG pipeline initialized")
    
    # Initialize file processor with MAXIMUM-SPEED chunk settings
    # HUGE chunks = minimum embedding calls = FASTEST processing
    file_processor = FileProcessor(
        chunk_size=8000,      # HUGE chunks = ~600 chunks for 5MB PDF
        chunk_overlap=200,    # Small overlap
        min_chunk_size=500    # Filter out small chunks
    )
    logger.info("✅ File processor initialized (chunk_size: 8000, MAXIMUM-SPEED)")
    
    # Initialize web crawler with matching settings
    web_crawler = WebCrawler(chunk_size=1500, chunk_overlap=150)
    logger.info("✅ Web crawler initialized")
    
    # Initialize Redis
    try:
        redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        redis_client.ping()
        logger.info("✅ Redis connected")
    except Exception as e:
        logger.warning(f"⚠️ Redis connection failed: {e}")
        redis_client = None
    
    # Initialize Document Processor for workers
    document_processor = DocumentProcessor(
        file_processor=file_processor,
        embedding_service=embedding_service,
        retriever=retriever,
        minio_service=minio_service,
        db_service=db_service
    )
    
    # Initialize Worker Pool for parallel document processing
    num_workers = int(os.getenv("DOC_WORKERS", "5"))  # Default 5 workers for speed
    worker_pool = WorkerPool(
        num_workers=num_workers,
        redis_url=settings.redis_url,
        process_func=document_processor.process_document
    )
    await worker_pool.start()
    logger.info(f"✅ Worker pool started ({num_workers} workers)")
    
    # Inject dependencies into routers
    chat.set_rag_pipeline(rag_pipeline)
    knowledge.set_services(
        file_processor,
        web_crawler,
        embedding_service,
        retriever,
        minio_service,
        db_service,
        worker_pool  # Add worker pool
    )
    
    # Set up admin service checks
    async def check_qdrant():
        if retriever:
            stats = await retriever.get_stats()
            return {"healthy": "error" not in stats, "details": stats}
        return {"healthy": False, "details": {"error": "Not initialized"}}
    
    async def check_redis():
        if redis_client:
            try:
                redis_client.ping()
                info = redis_client.info("memory")
                return {
                    "healthy": True,
                    "details": {"memory": info.get("used_memory_human")}
                }
            except:
                pass
        return {"healthy": False}
    
    async def check_minio():
        if minio_service:
            try:
                healthy = minio_service.health_check()
                return {"healthy": healthy, "details": {"bucket": minio_service.bucket_name}}
            except:
                pass
        return {"healthy": False, "details": {"error": "Not initialized"}}
    
    async def check_postgres():
        if db_service:
            try:
                healthy = await db_service.health_check()
                stats = await db_service.get_stats() if healthy else {}
                return {"healthy": healthy, "details": stats.get("documents", {})}
            except:
                pass
        return {"healthy": False, "details": {"error": "Not initialized"}}
    
    admin.set_check_functions({
        "qdrant": check_qdrant,
        "redis": check_redis,
        "minio": check_minio,
        "postgres": check_postgres
    })
    
    logger.info("✅ AI Power System started successfully!")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down AI Power System...")
    
    # Stop worker pool first
    if worker_pool:
        await worker_pool.stop()
        logger.info("✅ Worker pool stopped")
    
    # Close embedding service HTTP client
    if embedding_service:
        await embedding_service.close()
    
    if db_service:
        await db_service.disconnect()
    
    if redis_client:
        redis_client.close()
    
    logger.info("👋 Shutdown complete")


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="AI Power System",
    description="All-in-One AI Platform with RAG, Local LLM, and Knowledge Management",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router)
app.include_router(knowledge.router)
app.include_router(admin.router)


# ============================================================
# CORE ENDPOINTS
# ============================================================

@app.get("/", tags=["General"])
async def root():
    """API root with navigation"""
    return {
        "name": "AI Power System",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "chat": "/api/chat",
            "knowledge": "/api/knowledge",
            "admin": "/api/admin"
        }
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check for all services"""
    status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }
    
    # Check Ollama
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.ollama_base_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                status["services"]["ollama"] = {
                    "status": "healthy",
                    "models": len(models)
                }
            else:
                status["services"]["ollama"] = {"status": "unhealthy"}
                status["status"] = "degraded"
    except:
        status["services"]["ollama"] = {"status": "unreachable"}
        status["status"] = "degraded"
    
    # Check Qdrant
    if retriever:
        try:
            stats = await retriever.get_stats()
            if "error" not in stats:
                status["services"]["qdrant"] = {
                    "status": "healthy",
                    "vectors": stats.get("vectors_count", 0)
                }
            else:
                status["services"]["qdrant"] = {"status": "unhealthy"}
                status["status"] = "degraded"
        except:
            status["services"]["qdrant"] = {"status": "error"}
            status["status"] = "degraded"
    else:
        status["services"]["qdrant"] = {"status": "not_initialized"}
    
    # Check Redis
    if redis_client:
        try:
            redis_client.ping()
            status["services"]["redis"] = {"status": "healthy"}
        except:
            status["services"]["redis"] = {"status": "unhealthy"}
            status["status"] = "degraded"
    else:
        status["services"]["redis"] = {"status": "not_initialized"}
    
    # Check MinIO
    if minio_service:
        try:
            if minio_service.health_check():
                status["services"]["minio"] = {"status": "healthy"}
            else:
                status["services"]["minio"] = {"status": "unhealthy"}
                status["status"] = "degraded"
        except:
            status["services"]["minio"] = {"status": "error"}
            status["status"] = "degraded"
    else:
        status["services"]["minio"] = {"status": "not_initialized"}
    
    # Check PostgreSQL
    if db_service:
        try:
            if await db_service.health_check():
                status["services"]["postgres"] = {"status": "healthy"}
            else:
                status["services"]["postgres"] = {"status": "unhealthy"}
                status["status"] = "degraded"
        except:
            status["services"]["postgres"] = {"status": "error"}
            status["status"] = "degraded"
    else:
        status["services"]["postgres"] = {"status": "not_initialized"}
    
    # Check n8n
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://n8n:5678/healthz")
            if response.status_code == 200:
                status["services"]["n8n"] = {
                    "status": "healthy",
                    "url": "http://localhost:5678"
                }
            else:
                status["services"]["n8n"] = {"status": "unhealthy"}
                status["status"] = "degraded"
    except:
        status["services"]["n8n"] = {"status": "unreachable"}
        status["status"] = "degraded"
    
    return status


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.app_debug else "An unexpected error occurred"
        }
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.app_debug
    )
