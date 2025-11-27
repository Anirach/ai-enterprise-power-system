# AI Power System - Docker Setup Guide

> **Project:** AI Enterprise Power System  
> **Version:** 2.1  
> **Date:** November 2025  
> **Purpose:** Complete setup guide for Docker-based AI Knowledge Platform with RAG  
> **Languages:** English, Thai (full OCR support)

---

## Table of Contents

1. [System Architecture Overview](#system-architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Project Structure](#project-structure)
4. [Environment Configuration](#environment-configuration)
5. [Docker Compose Configuration](#docker-compose-configuration)
6. [Backend Setup (FastAPI)](#backend-setup)
7. [Frontend Setup (Next.js)](#frontend-setup)
8. [Database Initialization](#database-initialization)
9. [Deployment Commands](#deployment-commands)
10. [Service Access Summary](#service-access-summary)
11. [Common Operations](#common-operations)
12. [API Reference](#api-reference)
13. [Troubleshooting](#troubleshooting)

---

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Docker Network (ai-power-network)                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                        Frontend (Next.js) :3000                        │ │
│  │  ├── Chat Interface (RAG-powered)                                      │ │
│  │  ├── Knowledge Base Management (Upload, View, Delete)                  │ │
│  │  └── Admin Dashboard (Service Status, Model Management)                │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                      │                                       │
│                                      ▼                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                        Backend (FastAPI) :8000                         │ │
│  │  ├── RAG Pipeline (Embed → Search → Generate)                          │ │
│  │  ├── Document Processing:                                              │ │
│  │  │   • PDF: pdfplumber + Tesseract OCR (Thai support)                  │ │
│  │  │   • DOCX/PPTX/XLSX: Docling (IBM)                                   │ │
│  │  ├── Embeddings: sentence-transformers (fast batch processing)         │ │
│  │  ├── Worker Pool (5 parallel document processors)                      │ │
│  │  └── REST API + Admin Endpoints                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                      │                                       │
│           ┌──────────────────────────┼──────────────────────────┐           │
│           ▼                          ▼                          ▼           │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐         │
│  │     Ollama      │    │     Qdrant      │    │   PostgreSQL    │         │
│  │   (Local LLM)   │    │   (Vector DB)   │    │   (Metadata)    │         │
│  │     :11434      │    │     :6333       │    │     :5432       │         │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘         │
│                                                                              │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐         │
│  │      MinIO      │    │      Redis      │    │       n8n       │         │
│  │ (Object Storage)│    │     (Cache)     │    │  (Automation)   │         │
│  │   :9000/:9001   │    │     :6379       │    │     :5678       │         │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Summary

| Component | Technology | Purpose | Port(s) |
|-----------|------------|---------|---------|
| Frontend | Next.js 14 | User Interface (Chat, Knowledge Base, Admin) | 3000 |
| Backend | FastAPI | REST API, RAG Pipeline, Document Processing | 8000 |
| Local LLM | Ollama | Text generation (llama3.2:3b) | 11434 |
| Embeddings | sentence-transformers | Fast batch embedding (all-MiniLM-L6-v2) | - |
| Vector DB | Qdrant | Semantic search & embeddings storage | 6333, 6334 |
| Object Storage | MinIO | Document file storage | 9000 (API), 9001 (Console) |
| Database | PostgreSQL | Document metadata, user data | 5432 |
| Task Queue | Redis | Document processing queue + caching | 6379 |
| Automation | n8n | Workflow automation | 5678 |

### Document Processing Pipeline

| File Type | Parser | OCR Support | Notes |
|-----------|--------|-------------|-------|
| **PDF** | pdfplumber + Tesseract | ✅ Thai, English | Best for scanned documents |
| **DOCX** | Docling (IBM) | - | Microsoft Word |
| **PPTX** | Docling (IBM) | - | PowerPoint |
| **XLSX** | Docling (IBM) | - | Excel |
| **HTML** | Docling (IBM) | - | Web pages |
| **Images** | Docling + Tesseract | ✅ Thai, English | PNG, JPG, TIFF |
| **TXT/MD/CSV** | Native Python | - | Plain text |

### Embedding Performance

| Method | Speed | Use Case |
|--------|-------|----------|
| **sentence-transformers** (Default) | ~800 chunks/sec | Batch processing |
| Ollama (nomic-embed-text) | ~1 chunk/sec | On-demand queries |

### Data Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         Document Upload Flow                              │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│   User Upload ──► Backend API ──┬──► MinIO (store original file)         │
│                                 │                                         │
│                                 ├──► PostgreSQL (store metadata)          │
│                                 │    • name, size, page_count             │
│                                 │    • word_count, language, tags         │
│                                 │                                         │
│                                 └──► Redis Task Queue ──► Worker Pool    │
│                                                              │            │
│                                      ┌───────────────────────┘            │
│                                      ▼                                    │
│                                 Parse Document:                           │
│                                 • PDF: pdfplumber + OCR (Thai support)   │
│                                 • DOCX/PPTX: Docling                      │
│                                      │                                    │
│                                      ▼                                    │
│                                 sentence-transformers (batch embed)       │
│                                      │                                    │
│                                      ▼                                    │
│                                 Qdrant (store vectors)                    │
│                                                                           │
├──────────────────────────────────────────────────────────────────────────┤
│                         Document Delete Flow                              │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│   User Delete ──► Backend API ──┬──► MinIO (delete file)                 │
│                                 ├──► PostgreSQL (delete record)           │
│                                 └──► Qdrant (delete vectors)              │
│                                                                           │
├──────────────────────────────────────────────────────────────────────────┤
│                            RAG Query Flow                                 │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│   User Question ──► sentence-transformers (embed) ──► Qdrant (search)    │
│                                                           │               │
│                                                           ▼               │
│                           Ollama (generate with context) ──► Answer      │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 16 GB | 32+ GB |
| CPU | 4 cores | 8+ cores |
| Storage | 50 GB SSD | 100+ GB NVMe |
| Docker | 24.0+ | Latest |
| OS | macOS / Linux / Windows (WSL2) | macOS / Ubuntu 22.04+ |

### Install Docker

#### macOS
```bash
# Using Homebrew
brew install --cask docker

# Start Docker Desktop and configure resources
# Docker Desktop > Settings > Resources > Memory: 16GB+
```

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install docker.io docker-compose-v2
sudo usermod -aG docker $USER
newgrp docker
```

#### Verify Installation
```bash
docker --version
docker compose version
```

---

## Project Structure

```
ai-enterprise-power-system/
├── docker-compose.yml              # Main Docker orchestration
├── .env                            # Environment variables (gitignored)
├── .env.example                    # Environment template
├── README.md                       # Project documentation
│
├── frontend/                       # Next.js Frontend
│   ├── Dockerfile
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   └── src/
│       ├── app/
│       │   ├── page.tsx            # Chat interface
│       │   ├── knowledge/page.tsx  # Knowledge base management
│       │   ├── admin/page.tsx      # Admin dashboard
│       │   ├── layout.tsx
│       │   └── globals.css
│       └── components/
│           └── Sidebar.tsx
│
├── backend/                        # FastAPI Backend
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/
│       ├── main.py                 # FastAPI app entry
│       ├── config.py               # Configuration
│       ├── rag/
│       │   ├── embeddings.py       # sentence-transformers + Ollama embeddings
│       │   ├── retriever.py        # Qdrant retrieval
│       │   └── pipeline.py         # RAG orchestration
│       ├── services/
│       │   ├── file_processor.py   # PDF (pdfplumber+OCR), DOCX (Docling)
│       │   ├── web_crawler.py      # Web content extraction
│       │   ├── minio_service.py    # MinIO file operations
│       │   └── database.py         # PostgreSQL operations
│       ├── workers/
│       │   ├── task_queue.py       # Redis task queue
│       │   └── document_processor.py # Parallel document processor
│       └── routers/
│           ├── chat.py             # Chat API endpoints
│           ├── knowledge.py        # Knowledge base API
│           └── admin.py            # Admin API endpoints
│
├── postgres/
│   └── init/
│       └── init.sql                # Database initialization
│
└── nginx/                          # (Optional) Reverse proxy
    └── nginx.conf
```

---

## Environment Configuration

### Create `.env` File

```bash
# ============================================================
# AI POWER SYSTEM - ENVIRONMENT CONFIGURATION
# ============================================================

# ==================== General ====================
COMPOSE_PROJECT_NAME=ai-power-system
TIMEZONE=Asia/Bangkok

# ==================== PostgreSQL ====================
POSTGRES_USER=aipower
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_DB=aipower_db
POSTGRES_PORT=5432

# ==================== Redis ====================
REDIS_PORT=6379

# ==================== Qdrant ====================
QDRANT_PORT=6333
QDRANT_GRPC_PORT=6334

# ==================== Ollama ====================
OLLAMA_PORT=11434
OLLAMA_DEFAULT_MODEL=llama3.2:3b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# ==================== MinIO (Object Storage) ====================
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin123
MINIO_BUCKET=documents
MINIO_API_PORT=9000
MINIO_CONSOLE_PORT=9001

# ==================== n8n ====================
N8N_PORT=5678
N8N_BASIC_AUTH_ACTIVE=true
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=your_n8n_password
N8N_ENCRYPTION_KEY=your_32_character_encryption_key

# ==================== Application ====================
FRONTEND_PORT=3000
BACKEND_PORT=8000
APP_SECRET_KEY=your_app_secret_key
APP_DEBUG=false
APP_LOG_LEVEL=INFO

# ==================== External AI APIs (Optional) ====================
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
```

### Generate Secure Passwords
```bash
# Generate random password
openssl rand -base64 32

# Generate encryption key
openssl rand -hex 16
```

---

## Docker Compose Configuration

### `docker-compose.yml`

```yaml
services:
  # ==================== FRONTEND (Next.js) ====================
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: ai-frontend
    ports:
      - "${FRONTEND_PORT:-3000}:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
      - NODE_ENV=production
    networks:
      - ai-network
    depends_on:
      - backend
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # ==================== BACKEND (FastAPI) ====================
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: ai-backend
    ports:
      - "${BACKEND_PORT:-8000}:8000"
    environment:
      - APP_SECRET_KEY=${APP_SECRET_KEY}
      - APP_DEBUG=${APP_DEBUG:-false}
      - APP_LOG_LEVEL=${APP_LOG_LEVEL:-INFO}
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - REDIS_URL=redis://redis:6379/0
      - QDRANT_HOST=qdrant
      - QDRANT_PORT=6333
      - OLLAMA_BASE_URL=http://ollama:11434
      - OLLAMA_DEFAULT_MODEL=${OLLAMA_DEFAULT_MODEL:-llama3.2:3b}
      - OLLAMA_EMBEDDING_MODEL=${OLLAMA_EMBEDDING_MODEL:-nomic-embed-text}
      - MINIO_ENDPOINT=minio:9000
      - MINIO_ACCESS_KEY=${MINIO_ROOT_USER:-minioadmin}
      - MINIO_SECRET_KEY=${MINIO_ROOT_PASSWORD:-minioadmin123}
      - MINIO_BUCKET=${MINIO_BUCKET:-documents}
      - TZ=${TIMEZONE:-Asia/Bangkok}
    volumes:
      - ./backend/src:/app/src:ro
      - upload_data:/app/uploads
    networks:
      - ai-network
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      qdrant:
        condition: service_healthy
      minio:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s

  # ==================== OLLAMA (Local LLM) ====================
  ollama:
    image: ollama/ollama:latest
    container_name: ai-ollama
    ports:
      - "${OLLAMA_PORT:-11434}:11434"
    volumes:
      - ollama_data:/root/.ollama
    networks:
      - ai-network
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 8G
        reservations:
          memory: 4G
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:11434/api/tags || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  # ==================== QDRANT (Vector Database) ====================
  qdrant:
    image: qdrant/qdrant:latest
    container_name: ai-qdrant
    ports:
      - "${QDRANT_PORT:-6333}:6333"
      - "${QDRANT_GRPC_PORT:-6334}:6334"
    volumes:
      - qdrant_data:/qdrant/storage
    environment:
      - QDRANT__SERVICE__HTTP_PORT=6333
      - QDRANT__SERVICE__GRPC_PORT=6334
      - QDRANT__LOG_LEVEL=INFO
    networks:
      - ai-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "bash -c 'echo > /dev/tcp/localhost/6333'"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 30s

  # ==================== MINIO (Object Storage) ====================
  minio:
    image: minio/minio:latest
    container_name: ai-minio
    ports:
      - "${MINIO_API_PORT:-9000}:9000"
      - "${MINIO_CONSOLE_PORT:-9001}:9001"
    environment:
      - MINIO_ROOT_USER=${MINIO_ROOT_USER:-minioadmin}
      - MINIO_ROOT_PASSWORD=${MINIO_ROOT_PASSWORD:-minioadmin123}
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data
    networks:
      - ai-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s

  # ==================== POSTGRESQL ====================
  postgres:
    image: postgres:16-alpine
    container_name: ai-postgres
    ports:
      - "${POSTGRES_PORT:-5432}:5432"
    environment:
      - POSTGRES_USER=${POSTGRES_USER:-aipower}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB:-aipower_db}
      - PGDATA=/var/lib/postgresql/data/pgdata
      - TZ=${TIMEZONE:-Asia/Bangkok}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./postgres/init:/docker-entrypoint-initdb.d:ro
    networks:
      - ai-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-aipower} -d ${POSTGRES_DB:-aipower_db}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

  # ==================== REDIS (Cache) ====================
  redis:
    image: redis:7-alpine
    container_name: ai-redis
    ports:
      - "${REDIS_PORT:-6379}:6379"
    command: >
      redis-server 
      --appendonly yes 
      --maxmemory 512mb 
      --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    networks:
      - ai-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 10s

  # ==================== N8N (Automation) ====================
  n8n:
    image: n8nio/n8n:latest
    container_name: ai-n8n
    ports:
      - "${N8N_PORT:-5678}:5678"
    environment:
      - N8N_BASIC_AUTH_ACTIVE=${N8N_BASIC_AUTH_ACTIVE:-true}
      - N8N_BASIC_AUTH_USER=${N8N_BASIC_AUTH_USER:-admin}
      - N8N_BASIC_AUTH_PASSWORD=${N8N_BASIC_AUTH_PASSWORD}
      - N8N_ENCRYPTION_KEY=${N8N_ENCRYPTION_KEY}
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=postgres
      - DB_POSTGRESDB_PORT=5432
      - DB_POSTGRESDB_DATABASE=${POSTGRES_DB:-aipower_db}
      - DB_POSTGRESDB_USER=${POSTGRES_USER:-aipower}
      - DB_POSTGRESDB_PASSWORD=${POSTGRES_PASSWORD}
      - DB_POSTGRESDB_SCHEMA=n8n
      - N8N_HOST=0.0.0.0
      - WEBHOOK_URL=http://localhost:5678/
      - GENERIC_TIMEZONE=${TIMEZONE:-Asia/Bangkok}
    volumes:
      - n8n_data:/home/node/.n8n
    networks:
      - ai-network
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped

# ==================== NETWORKS ====================
networks:
  ai-network:
    name: ai-power-network
    driver: bridge

# ==================== VOLUMES ====================
volumes:
  ollama_data:
    name: ai-ollama-data
  qdrant_data:
    name: ai-qdrant-data
  postgres_data:
    name: ai-postgres-data
  redis_data:
    name: ai-redis-data
  n8n_data:
    name: ai-n8n-data
  upload_data:
    name: ai-upload-data
  minio_data:
    name: ai-minio-data
```

---

## Backend Setup

### `backend/Dockerfile`

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies including OCR support for Thai
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libfontconfig1 \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-tha \
    fonts-thai-tlwg \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user with home directory
RUN groupadd -r appuser && useradd -r -g appuser -d /home/appuser -m appuser

# Create required directories
RUN mkdir -p /app/uploads /home/appuser/.cache/huggingface \
    && chown -R appuser:appuser /app/uploads /home/appuser

# Set home and cache directories for docling/huggingface
ENV HOME=/home/appuser \
    HF_HOME=/home/appuser/.cache/huggingface

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && chmod -R o+r /usr/local/lib/python3.12/site-packages/ \
    && find /usr/local/lib/python3.12/site-packages/ -type d -exec chmod o+rx {} \;

# Copy application code
COPY src/ ./src/

# Change ownership
RUN chown -R appuser:appuser /app

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### `backend/requirements.txt`

```txt
# Web Framework
fastapi>=0.110.0
uvicorn[standard]>=0.30.0
python-multipart>=0.0.9

# Database
sqlalchemy>=2.0.30
asyncpg>=0.29.0
psycopg2-binary>=2.9.9
alembic>=1.13.0

# Redis (for task queue)
redis>=5.0.0

# Vector Database
qdrant-client>=1.10.0

# Object Storage (MinIO)
minio>=7.2.0

# HTTP Client
httpx>=0.27.0
aiohttp>=3.9.0

# Data Validation
pydantic-settings>=2.2.0

# Document Processing (Docling for DOCX/PPTX)
docling>=2.0.0

# PDF Processing (better Thai support)
pypdf>=4.0.0
pdfplumber>=0.11.0
pdf2image>=1.17.0
Pillow>=10.0.0

# FAST Embeddings (sentence-transformers - batch processing)
sentence-transformers>=2.7.0
torch>=2.0.0

# Web Crawling
beautifulsoup4>=4.12.0
lxml>=5.0.0

# Text Processing
langchain-text-splitters>=0.2.0

# Security
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4

# Utilities
python-dotenv>=1.0.0
orjson>=3.10.0
aiofiles>=24.0.0
jinja2>=3.1.0
psutil>=6.0.0
```

---

## Frontend Setup

### `frontend/Dockerfile`

```dockerfile
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT=3000
CMD ["node", "server.js"]
```

### `frontend/package.json`

```json
{
  "name": "ai-power-frontend",
        "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  },
  "dependencies": {
    "next": "14.2.15",
    "react": "^18",
    "react-dom": "^18",
    "lucide-react": "^0.454.0"
  },
  "devDependencies": {
    "@types/node": "^20",
    "@types/react": "^18",
    "@types/react-dom": "^18",
    "autoprefixer": "^10.4.20",
    "postcss": "^8.4.47",
    "tailwindcss": "^3.4.14",
    "typescript": "^5"
  }
}
```

---

## Database Initialization

### `postgres/init/init.sql`

```sql
-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- N8N Schema
CREATE SCHEMA IF NOT EXISTS n8n;

-- Documents Table (with MinIO and metadata support)
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    -- Basic file info
    name VARCHAR(500) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    content_type VARCHAR(100),
    file_size BIGINT DEFAULT 0,
    -- MinIO storage
    minio_bucket VARCHAR(100),
    minio_object_key VARCHAR(500),
    -- Content and processing
    content TEXT,
    chunks_count INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    -- Document metadata
    page_count INTEGER DEFAULT 0,
    word_count INTEGER DEFAULT 0,
    language VARCHAR(20) DEFAULT 'unknown',
    tags TEXT[] DEFAULT '{}',
    -- Extra metadata as JSON
    metadata JSONB DEFAULT '{}',
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Chunks Table
CREATE TABLE IF NOT EXISTS chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding_id VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Chat History Table
CREATE TABLE IF NOT EXISTS chat_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    sources JSONB DEFAULT '[]',
    model VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Users Table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- System Config Table
CREATE TABLE IF NOT EXISTS system_config (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_created ON documents(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_documents_name ON documents USING gin(name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_documents_tags ON documents USING gin(tags);
CREATE INDEX IF NOT EXISTS idx_documents_language ON documents(language);
CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks(embedding_id);
CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_history(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_created ON chat_history(created_at DESC);

-- Update Trigger
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Initial Config
INSERT INTO system_config (key, value, description) VALUES
    ('default_model', '"llama3.2:3b"', 'Default AI model'),
    ('embedding_model', '"nomic-embed-text"', 'Embedding model'),
    ('chunk_size', '1000', 'Document chunk size'),
    ('chunk_overlap', '200', 'Chunk overlap'),
    ('version', '"2.0.0"', 'System version')
ON CONFLICT (key) DO NOTHING;

-- Permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO aipower;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO aipower;
GRANT ALL PRIVILEGES ON SCHEMA n8n TO aipower;
```

---

## Deployment Commands

### Initial Setup

```bash
# Navigate to project directory
cd ai-enterprise-power-system

# Create .env file
cp .env.example .env
# Edit with your passwords
nano .env

# Build and start all services
docker compose up -d --build

# View logs
docker compose logs -f
```

### Pull AI Models

```bash
# Pull conversational model
docker exec ai-ollama ollama pull llama3.2:3b

# Pull embedding model
docker exec ai-ollama ollama pull nomic-embed-text

# Verify models
docker exec ai-ollama ollama list
```

### Verify Services

```bash
# Check all services
docker compose ps

# Health check
curl http://localhost:8000/health | jq

# Test frontend
curl -I http://localhost:3000

# Test MinIO Console
curl -I http://localhost:9001
```

---

## Service Access Summary

| Service | URL | Credentials | Description |
|---------|-----|-------------|-------------|
| **Frontend** | http://localhost:3000 | - | Main user interface |
| **Backend API** | http://localhost:8000 | - | REST API |
| **API Docs** | http://localhost:8000/docs | - | Swagger documentation |
| **MinIO Console** | http://localhost:9001 | minioadmin / minioadmin123 | File storage UI |
| **n8n** | http://localhost:5678 | admin / (your password) | Workflow automation |
| **Qdrant Dashboard** | http://localhost:6333/dashboard | - | Vector database UI |

### Port Overview

```
┌────────────────────────────────────────────────────────────┐
│                      PORT MAPPING                          │
├────────────────────────────────────────────────────────────┤
│  3000  │ Frontend (Next.js)                                │
│  8000  │ Backend API (FastAPI)                             │
│  9000  │ MinIO API                                         │
│  9001  │ MinIO Console (Web UI)                            │
│  5678  │ n8n Automation                                    │
│  6333  │ Qdrant REST API                                   │
│  6334  │ Qdrant gRPC                                       │
│  11434 │ Ollama API                                        │
│  5432  │ PostgreSQL                                        │
│  6379  │ Redis                                             │
└────────────────────────────────────────────────────────────┘
```

---

## API Reference

### Knowledge Base API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/knowledge/upload` | Upload document |
| GET | `/api/knowledge/documents` | List all documents |
| GET | `/api/knowledge/documents/{id}` | Get document details |
| GET | `/api/knowledge/documents/{id}/content` | Get document content |
| GET | `/api/knowledge/documents/{id}/download` | Download original file |
| DELETE | `/api/knowledge/documents/{id}` | Delete document |
| DELETE | `/api/knowledge/clear-all` | Delete ALL documents |
| PATCH | `/api/knowledge/documents/{id}/tags` | Update tags |
| POST | `/api/knowledge/crawl` | Crawl website |
| GET | `/api/knowledge/stats` | Get statistics |
| GET | `/api/knowledge/workers/stats` | Worker pool status |

### Chat API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat/` | Chat with RAG |
| POST | `/api/chat/query` | Direct RAG query |

### Admin API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/services` | Service status |
| GET | `/api/admin/models` | List AI models |
| POST | `/api/admin/models/pull` | Pull new model |
| GET | `/api/admin/system-info` | System information |

---

## Common Operations

### Service Management

```bash
# Stop all services
docker compose down

# Stop and remove data (CAUTION!)
docker compose down -v

# Restart specific service
docker compose restart backend
docker compose restart frontend

# Rebuild service
docker compose up -d --build backend
```

### Logs

```bash
# View all logs
docker compose logs -f

# View specific service
docker compose logs -f backend
docker compose logs -f frontend

# View last 100 lines
docker compose logs --tail=100 backend
```

### Database Operations

```bash
# Access PostgreSQL
docker exec -it ai-postgres psql -U aipower -d aipower_db

# Backup database
docker exec ai-postgres pg_dump -U aipower aipower_db > backup.sql

# Restore database
cat backup.sql | docker exec -i ai-postgres psql -U aipower aipower_db
```

### MinIO Operations

```bash
# Access MinIO console at http://localhost:9001

# List buckets (via mc client)
docker exec ai-minio mc ls local
```

---

## Troubleshooting

### Container Not Starting

```bash
# Check logs
docker compose logs <service-name>

# Check port conflicts
sudo lsof -i :8000
sudo lsof -i :3000
```

### Database Connection Issues

```bash
# Test PostgreSQL
docker exec ai-postgres pg_isready -U aipower

# Check connectivity
docker exec ai-backend ping postgres
```

### Qdrant Issues

```bash
# Check Qdrant health
curl http://localhost:6333/health

# View Qdrant logs
docker compose logs qdrant
```

### MinIO Issues

```bash
# Check MinIO health
curl http://localhost:9000/minio/health/live

# View MinIO logs
docker compose logs minio
```

### Thai Language Support

The system fully supports Thai documents:

```bash
# Verify Thai OCR is installed
docker exec ai-backend tesseract --list-langs
# Should show: eng, tha

# Test Thai PDF processing
curl -X POST http://localhost:8000/api/knowledge/upload \
  -F "file=@thai_document.pdf"

# Check processing status
curl http://localhost:8000/api/knowledge/documents | jq '.[0].status'
```

**Supported Thai processing:**
- ✅ PDF with embedded Thai text (pdfplumber)
- ✅ Scanned Thai PDFs (Tesseract OCR)
- ✅ Thai in DOCX/PPTX (Docling)
- ✅ Thai image OCR (PNG, JPG)

### Reset Everything

```bash
# Stop all
docker compose down

# Remove all volumes (DELETES ALL DATA)
docker compose down -v

# Remove all images
docker compose down --rmi all

# Clean Docker
docker system prune -a --volumes

# Rebuild
docker compose up -d --build
```

---

## Resource Requirements

### Memory Allocation

| Service | Limit | Reserved | Notes |
|---------|-------|----------|-------|
| Ollama | 8 GB | 4 GB | Varies by model (llama3.2:3b) |
| Qdrant | 4 GB | 2 GB | Depends on vectors |
| PostgreSQL | 2 GB | 1 GB | Document metadata |
| MinIO | 1 GB | 512 MB | File storage |
| Redis | 1 GB | 512 MB | Task queue + Cache |
| Backend | 4 GB | 2 GB | FastAPI + sentence-transformers + Docling |
| Frontend | 1 GB | 512 MB | Next.js |
| n8n | 2 GB | 1 GB | Workflows |
| **Total** | ~23 GB | ~12 GB | |

> **Note:** First document upload will download the sentence-transformers model (~90MB).
> This is cached for subsequent uses.

### Disk Space

| Component | Size | Notes |
|-----------|------|-------|
| Docker Images | ~15 GB | All services |
| Ollama Models | 5-50 GB | Depends on models |
| MinIO Data | Variable | Document files |
| PostgreSQL | Variable | Metadata |
| Qdrant | Variable | ~1GB per 1M vectors |
| **Recommended** | 100+ GB | |

---

## Document Information

| Property | Value |
|----------|-------|
| **Version** | 2.1 |
| **Last Updated** | November 2025 |
| **Project** | AI Enterprise Power System |
| **Stack** | Next.js + FastAPI + Ollama + sentence-transformers + Qdrant + MinIO + PostgreSQL |
| **Languages** | English, Thai (full OCR support) |

### Changelog (v2.1)

- **PDF Processing**: Switched from Docling to pdfplumber + Tesseract OCR for better Thai language support
- **Embeddings**: Added sentence-transformers for fast batch embedding (~800 chunks/sec vs ~1 chunk/sec with Ollama)
- **Worker Pool**: Implemented Redis-based task queue with 5 parallel document processors
- **Thai Support**: Added tesseract-ocr-tha and Thai fonts for proper OCR
- **Clear All**: Added endpoint to delete all documents at once

---

*For support, refer to the project README or check the GitHub repository.*
