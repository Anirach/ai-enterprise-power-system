# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Power System is a Docker-based AI knowledge management platform combining RAG (Retrieval Augmented Generation), local LLM via Ollama, document processing, and workflow automation. The system supports Thai and English languages.

## Architecture

```
Frontend (Next.js 14) :3000
    ↓
Backend (FastAPI) :8000
    ├── RAG Pipeline (sentence-transformers embeddings + Qdrant)
    ├── Document Processing (5 parallel workers via Redis queue)
    ├── File Processing (Docling + pdfplumber + Tesseract OCR)
    └── REST API

Services:
├── Ollama :11434 (Local LLM - llama3.2:3b default)
├── Qdrant :6333 (Vector database)
├── PostgreSQL :5432 (Document metadata)
├── Redis :6379 (Task queue + cache + active model)
├── MinIO :9000 (Object storage)
└── n8n :5678 (Workflow automation)
```

## Build & Run Commands

```bash
# Start all services
docker compose up -d --build

# View logs
docker compose logs -f
docker compose logs -f backend  # specific service

# Stop services
docker compose down

# Local backend development
cd backend && pip install -r requirements.txt && uvicorn src.main:app --reload

# Local frontend development
cd frontend && npm install && npm run dev
```

## Key Backend Structure

- `backend/src/main.py` - FastAPI app initialization with lifespan for service setup
- `backend/src/config.py` - Pydantic BaseSettings for environment configuration
- `backend/src/routers/` - API endpoints (chat.py, knowledge.py, admin.py)
- `backend/src/rag/` - RAG pipeline (embeddings.py uses LocalEmbeddingService, pipeline.py, retriever.py)
- `backend/src/services/` - Core services (database.py, file_processor.py, minio_service.py, web_crawler.py)
- `backend/src/workers/` - Redis-based task queue and document processors

## Key Frontend Structure

- `frontend/src/app/page.tsx` - Main chat interface with RAG toggle
- `frontend/src/app/knowledge/page.tsx` - Document upload and web crawling
- `frontend/src/app/admin/page.tsx` - Service monitoring and model management
- `frontend/next.config.js` - API rewrites proxy `/api/*` to backend

## API Endpoints

- `POST /api/chat/query` - RAG query with streaming
- `POST /api/knowledge/upload` - Document upload
- `POST /api/knowledge/crawl` - Website crawling
- `GET /api/knowledge/documents` - List documents
- `GET /api/admin/health` - System health check
- `GET/POST /api/admin/models/active` - Active model management via Redis

## Development Patterns

**Backend:**
- Services are initialized during FastAPI lifespan and injected as global variables
- All database/external service calls use async/await
- Document processing uses a Redis-based task queue with worker pool

**Frontend:**
- Client-side components with React hooks
- Markdown rendering uses react-markdown with remark-gfm
- API calls through Next.js rewrites to avoid CORS

## Performance Configuration

- Local embeddings via sentence-transformers (all-MiniLM-L6-v2, 384 dimensions)
- Embedding cache: 5000 entries default
- Chunk size: 8000 characters for minimal embedding calls
- Worker pool: 5 parallel document processors

## Environment Variables

Key settings in `.env`:
- `OLLAMA_DEFAULT_MODEL` - LLM model name
- `USE_LOCAL_EMBEDDINGS` - true for sentence-transformers (faster)
- `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `MINIO_BUCKET`
- `POSTGRES_PASSWORD`, `POSTGRES_USER`, `POSTGRES_DB`
- Database and service URLs are auto-configured for Docker network

## Thai Language Support

- Tesseract OCR configured for Thai (`tha+eng`)
- Thai fonts installed in backend Docker image
- Language detection for appropriate text processing
