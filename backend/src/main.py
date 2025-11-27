"""
AI Power System - Main Application
=====================================
FastAPI application with RAG pipeline, file processing, and web crawling.
Connects to Ollama, Qdrant, PostgreSQL, and Redis.
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
from .services import FileProcessor, WebCrawler
from .routers import chat, knowledge, admin

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


# ============================================================
# LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown"""
    global embedding_service, retriever, rag_pipeline, file_processor, web_crawler, redis_client
    
    logger.info("🚀 Starting AI Power System...")
    
    # Initialize embedding service
    embedding_service = EmbeddingService(
        base_url=settings.ollama_base_url,
        model=settings.ollama_embedding_model
    )
    logger.info(f"✅ Embedding service initialized (model: {settings.ollama_embedding_model})")
    
    # Initialize vector retriever
    try:
        retriever = VectorRetriever(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            dimension=768
        )
        logger.info("✅ Vector retriever connected to Qdrant")
    except Exception as e:
        logger.warning(f"⚠️ Qdrant connection failed: {e}")
        retriever = None
    
    # Initialize RAG pipeline
    if retriever:
        rag_pipeline = RAGPipeline(
            embedding_service=embedding_service,
            retriever=retriever,
            ollama_base_url=settings.ollama_base_url,
            default_model=settings.ollama_default_model
        )
        logger.info("✅ RAG pipeline initialized")
    
    # Initialize file processor
    file_processor = FileProcessor(chunk_size=1000, chunk_overlap=200)
    logger.info("✅ File processor initialized")
    
    # Initialize web crawler
    web_crawler = WebCrawler(chunk_size=1000, chunk_overlap=200)
    logger.info("✅ Web crawler initialized")
    
    # Initialize Redis
    try:
        redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        redis_client.ping()
        logger.info("✅ Redis connected")
    except Exception as e:
        logger.warning(f"⚠️ Redis connection failed: {e}")
        redis_client = None
    
    # Inject dependencies into routers
    chat.set_rag_pipeline(rag_pipeline)
    knowledge.set_services(
        file_processor,
        web_crawler,
        embedding_service,
        retriever,
        settings.upload_dir
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
    
    admin.set_check_functions({
        "qdrant": check_qdrant,
        "redis": check_redis
    })
    
    logger.info("✅ AI Power System started successfully!")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down AI Power System...")
    
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


