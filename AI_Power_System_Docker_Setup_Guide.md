# Docker-Based AI Knowledge System Setup Guide

> **Project:** VXIP Smart Knowledge Warehouse  
> **Version:** 1.0  
> **Date:** November 2025  
> **Purpose:** Complete setup guide for Docker-based AI infrastructure

---

## Table of Contents

1. [System Architecture Overview](#system-architecture-overview)
2. [Prerequisites](#step-1-prerequisites)
3. [Project Structure](#step-2-project-structure)
4. [Environment Configuration](#step-3-environment-configuration)
5. [Docker Compose Configuration](#step-4-docker-compose-configuration)
6. [Application Server Setup](#step-5-application-server-setup)
7. [Database Initialization](#step-6-database-initialization)
8. [Deployment Commands](#step-7-deployment-commands)
9. [Service Access Summary](#step-8-service-access-summary)
10. [Common Operations](#step-9-common-operations)
11. [Resource Usage Estimate](#resource-usage-estimate)
12. [Next Steps](#next-steps)
13. [Troubleshooting](#troubleshooting)

---

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Docker Network (ai-system-net)               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   Ollama     │  │    Neo4j     │  │    Qdrant    │              │
│  │  (AI Model)  │  │ (Graph DB)   │  │ (Vector DB)  │              │
│  │  :11434      │  │ :7474/:7687  │  │    :6333     │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │     n8n      │  │  PostgreSQL  │  │    Redis     │              │
│  │ (Automation) │  │  (Database)  │  │   (Cache)    │              │
│  │    :5678     │  │    :5432     │  │    :6379     │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              Application Server (FastAPI + Admin)            │   │
│  │                         :8000                                │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Summary

| Component | Technology | Purpose | Port |
|-----------|------------|---------|------|
| AI Local Model | Ollama | Local LLM inference | 11434 |
| Graph Database | Neo4j | Knowledge graph storage | 7474, 7687 |
| Vector Database | Qdrant | Semantic search & embeddings | 6333 |
| Automation | n8n | Workflow automation | 5678 |
| Database Server | PostgreSQL | Relational data storage | 5432 |
| Cache | Redis | Session & query caching | 6379 |
| Application Server | FastAPI | API & Admin interface | 8000 |
| DB Admin | Adminer | Database management UI | 8080 |

---

## Step 1: Prerequisites

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 16 GB | 32+ GB |
| CPU | 4 cores | 8+ cores |
| Storage | 50 GB SSD | 100+ GB NVMe |
| Docker | 24.0+ | Latest |
| OS | macOS / Linux / Windows with WSL2 | Ubuntu 22.04+ / macOS |

### Install Docker & Docker Compose

#### macOS

```bash
# Using Homebrew
brew install --cask docker

# Start Docker Desktop from Applications
# Configure resources in Docker Desktop > Settings > Resources
```

#### Ubuntu/Debian

```bash
# Update package index
sudo apt update

# Install Docker
sudo apt install docker.io docker-compose-v2

# Add user to docker group (avoid sudo)
sudo usermod -aG docker $USER

# Apply group changes (or logout/login)
newgrp docker
```

#### Windows (WSL2)

```powershell
# Install Docker Desktop for Windows
# Enable WSL2 backend in Docker Desktop settings
# Ensure WSL2 is installed and configured
```

#### Verify Installation

```bash
# Check Docker version
docker --version

# Check Docker Compose version
docker compose version

# Test Docker installation
docker run hello-world
```

### Additional Tools (Optional but Recommended)

```bash
# macOS
brew install jq yq curl

# Ubuntu/Debian
sudo apt install jq yq curl
```

---

## Step 2: Project Structure

### Create Directory Structure

```bash
# Create main project directory
mkdir -p ai-power-system
cd ai-power-system

# Create service directories
mkdir -p app/{src,templates,static}
mkdir -p postgres/init
mkdir -p n8n/data
mkdir -p neo4j/{data,logs,plugins}
mkdir -p qdrant/data
mkdir -p ollama/models
mkdir -p redis/data
```

### Expected Structure

```
ai-power-system/
├── docker-compose.yml          # Main Docker orchestration file
├── .env                        # Environment variables
├── .env.example                # Environment template
├── README.md                   # Project documentation
│
├── app/                        # Application server
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/
│       ├── main.py
│       ├── config.py
│       └── routers/
│
├── postgres/
│   └── init/
│       └── init.sql            # Database initialization
│
├── n8n/
│   └── data/                   # n8n persistent data
│
├── neo4j/
│   ├── data/                   # Graph data
│   ├── logs/                   # Neo4j logs
│   └── plugins/                # APOC and other plugins
│
├── qdrant/
│   └── data/                   # Vector data
│
├── ollama/
│   └── models/                 # AI model storage
│
└── redis/
    └── data/                   # Cache data
```

### Quick Setup Script

Create a setup script `setup.sh`:

```bash
#!/bin/bash

echo "🚀 Setting up AI Power System directory structure..."

# Create directories
mkdir -p ai-power-system/{app/{src,templates,static},postgres/init,n8n/data,neo4j/{data,logs,plugins},qdrant/data,ollama/models,redis/data}

cd ai-power-system

# Create placeholder files
touch .env
touch .env.example
touch README.md
touch docker-compose.yml
touch app/Dockerfile
touch app/requirements.txt
touch app/src/main.py
touch postgres/init/init.sql

echo "✅ Directory structure created!"
echo "📁 Location: $(pwd)"
```

Run with: `chmod +x setup.sh && ./setup.sh`

---

## Step 3: Environment Configuration

### Create `.env` File

```bash
# .env - Environment Configuration for AI Power System
# ⚠️ IMPORTANT: Never commit this file to version control

# ============ General Settings ============
COMPOSE_PROJECT_NAME=ai-power-system
TIMEZONE=Asia/Bangkok

# ============ PostgreSQL Configuration ============
POSTGRES_USER=aipower
POSTGRES_PASSWORD=your_secure_password_here_change_me
POSTGRES_DB=aipower_db
POSTGRES_PORT=5432

# ============ Neo4j Configuration ============
# Format: username/password
NEO4J_AUTH=neo4j/your_neo4j_password_change_me
NEO4J_HTTP_PORT=7474
NEO4J_BOLT_PORT=7687

# ============ Redis Configuration ============
REDIS_PORT=6379
REDIS_PASSWORD=

# ============ Qdrant Configuration ============
QDRANT_PORT=6333
QDRANT_GRPC_PORT=6334

# ============ Ollama Configuration ============
OLLAMA_PORT=11434
# Default model to load
OLLAMA_DEFAULT_MODEL=llama3.2:3b

# ============ n8n Configuration ============
N8N_PORT=5678
N8N_BASIC_AUTH_ACTIVE=true
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=your_n8n_password_change_me
# Generate with: openssl rand -hex 16
N8N_ENCRYPTION_KEY=your_32_character_encryption_key

# ============ Application Server ============
APP_PORT=8000
APP_SECRET_KEY=your_app_secret_key_change_me
APP_DEBUG=false
APP_LOG_LEVEL=INFO

# ============ External AI API (Optional) ============
# For Claude AI integration
ANTHROPIC_API_KEY=your_anthropic_api_key
# For OpenAI integration
OPENAI_API_KEY=your_openai_api_key
```

### Create `.env.example` Template

```bash
# .env.example - Template for environment configuration
# Copy this file to .env and fill in your values

COMPOSE_PROJECT_NAME=ai-power-system
TIMEZONE=Asia/Bangkok

# PostgreSQL
POSTGRES_USER=aipower
POSTGRES_PASSWORD=CHANGE_ME
POSTGRES_DB=aipower_db

# Neo4j
NEO4J_AUTH=neo4j/CHANGE_ME

# n8n
N8N_BASIC_AUTH_ACTIVE=true
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=CHANGE_ME
N8N_ENCRYPTION_KEY=GENERATE_32_CHAR_KEY

# Application
APP_SECRET_KEY=CHANGE_ME
APP_DEBUG=false
```

### Generate Secure Passwords

```bash
# Generate random password (32 characters)
openssl rand -base64 32

# Generate encryption key (hex, 32 characters)
openssl rand -hex 16

# Generate UUID-style key
uuidgen
```

---

## Step 4: Docker Compose Configuration

### Create `docker-compose.yml`

```yaml
version: '3.9'

# ============================================================
# AI POWER SYSTEM - DOCKER COMPOSE CONFIGURATION
# ============================================================
# Services included:
# - Ollama (AI Local Model)
# - Neo4j (Graph Database)
# - Qdrant (Vector Database)
# - n8n (Automation)
# - PostgreSQL (Database Server)
# - Redis (Cache)
# - FastAPI App (Application Server)
# - Adminer (Database Admin UI)
# ============================================================

services:
  # ==================== AI LOCAL MODEL ====================
  ollama:
    image: ollama/ollama:latest
    container_name: ai-ollama
    hostname: ollama
    ports:
      - "${OLLAMA_PORT:-11434}:11434"
    volumes:
      - ollama_data:/root/.ollama
    networks:
      - ai-system-net
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
      start_period: 40s
    labels:
      - "com.ai-power.service=ai-model"
      - "com.ai-power.description=Local LLM inference with Ollama"

  # ==================== GRAPH DATABASE ====================
  neo4j:
    image: neo4j:5.24.0-community
    container_name: ai-neo4j
    hostname: neo4j
    ports:
      - "${NEO4J_HTTP_PORT:-7474}:7474"   # HTTP Browser
      - "${NEO4J_BOLT_PORT:-7687}:7687"   # Bolt Protocol
    environment:
      - NEO4J_AUTH=${NEO4J_AUTH:-neo4j/password}
      - NEO4J_PLUGINS=["apoc"]
      - NEO4J_server_memory_heap_initial__size=1G
      - NEO4J_server_memory_heap_max__size=2G
      - NEO4J_server_memory_pagecache_size=1G
      - NEO4J_dbms_security_procedures_unrestricted=apoc.*
      - NEO4J_dbms_security_procedures_allowlist=apoc.*
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
      - neo4j_plugins:/plugins
    networks:
      - ai-system-net
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:7474 || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s
    labels:
      - "com.ai-power.service=graph-database"
      - "com.ai-power.description=Neo4j Knowledge Graph Database"

  # ==================== VECTOR DATABASE ====================
  qdrant:
    image: qdrant/qdrant:latest
    container_name: ai-qdrant
    hostname: qdrant
    ports:
      - "${QDRANT_PORT:-6333}:6333"       # REST API
      - "${QDRANT_GRPC_PORT:-6334}:6334"  # gRPC
    volumes:
      - qdrant_data:/qdrant/storage
    environment:
      - QDRANT__SERVICE__HTTP_PORT=6333
      - QDRANT__SERVICE__GRPC_PORT=6334
      - QDRANT__LOG_LEVEL=INFO
    networks:
      - ai-system-net
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:6333/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 20s
    labels:
      - "com.ai-power.service=vector-database"
      - "com.ai-power.description=Qdrant Vector Database for Embeddings"

  # ==================== N8N AUTOMATION ====================
  n8n:
    image: n8nio/n8n:latest
    container_name: ai-n8n
    hostname: n8n
    ports:
      - "${N8N_PORT:-5678}:5678"
    environment:
      # Authentication
      - N8N_BASIC_AUTH_ACTIVE=${N8N_BASIC_AUTH_ACTIVE:-true}
      - N8N_BASIC_AUTH_USER=${N8N_BASIC_AUTH_USER:-admin}
      - N8N_BASIC_AUTH_PASSWORD=${N8N_BASIC_AUTH_PASSWORD:-password}
      - N8N_ENCRYPTION_KEY=${N8N_ENCRYPTION_KEY}
      # Database
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=postgres
      - DB_POSTGRESDB_PORT=5432
      - DB_POSTGRESDB_DATABASE=${POSTGRES_DB:-aipower_db}
      - DB_POSTGRESDB_USER=${POSTGRES_USER:-aipower}
      - DB_POSTGRESDB_PASSWORD=${POSTGRES_PASSWORD}
      - DB_POSTGRESDB_SCHEMA=n8n
      # General
      - N8N_HOST=0.0.0.0
      - N8N_PROTOCOL=http
      - WEBHOOK_URL=http://localhost:5678/
      - GENERIC_TIMEZONE=${TIMEZONE:-Asia/Bangkok}
      - TZ=${TIMEZONE:-Asia/Bangkok}
      # Execution
      - EXECUTIONS_DATA_SAVE_ON_ERROR=all
      - EXECUTIONS_DATA_SAVE_ON_SUCCESS=all
      - EXECUTIONS_DATA_SAVE_MANUAL_EXECUTIONS=true
    volumes:
      - n8n_data:/home/node/.n8n
    networks:
      - ai-system-net
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G
    labels:
      - "com.ai-power.service=automation"
      - "com.ai-power.description=n8n Workflow Automation Platform"

  # ==================== DATABASE SERVER ====================
  postgres:
    image: postgres:16-alpine
    container_name: ai-postgres
    hostname: postgres
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
      - ai-system-net
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-aipower} -d ${POSTGRES_DB:-aipower_db}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    labels:
      - "com.ai-power.service=database"
      - "com.ai-power.description=PostgreSQL Database Server"

  # ==================== CACHE LAYER ====================
  redis:
    image: redis:7-alpine
    container_name: ai-redis
    hostname: redis
    ports:
      - "${REDIS_PORT:-6379}:6379"
    command: >
      redis-server 
      --appendonly yes 
      --maxmemory 512mb 
      --maxmemory-policy allkeys-lru
      --save 60 1
      --loglevel notice
    volumes:
      - redis_data:/data
    networks:
      - ai-system-net
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 10s
    labels:
      - "com.ai-power.service=cache"
      - "com.ai-power.description=Redis Cache Layer"

  # ==================== APPLICATION SERVER ====================
  app:
    build:
      context: ./app
      dockerfile: Dockerfile
    container_name: ai-app-server
    hostname: app
    ports:
      - "${APP_PORT:-8000}:8000"
    environment:
      # Application
      - APP_SECRET_KEY=${APP_SECRET_KEY}
      - APP_DEBUG=${APP_DEBUG:-false}
      - APP_LOG_LEVEL=${APP_LOG_LEVEL:-INFO}
      - TZ=${TIMEZONE:-Asia/Bangkok}
      # Database connections
      - DATABASE_URL=postgresql://${POSTGRES_USER:-aipower}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB:-aipower_db}
      - REDIS_URL=redis://redis:6379/0
      # Neo4j
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=${NEO4J_AUTH#*/}
      # Qdrant
      - QDRANT_HOST=qdrant
      - QDRANT_PORT=6333
      # Ollama
      - OLLAMA_BASE_URL=http://ollama:11434
      # External APIs (optional)
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}
      - OPENAI_API_KEY=${OPENAI_API_KEY:-}
    volumes:
      - ./app/src:/app/src:ro
      - app_data:/app/data
    networks:
      - ai-system-net
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      neo4j:
        condition: service_healthy
      qdrant:
        condition: service_healthy
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    labels:
      - "com.ai-power.service=application"
      - "com.ai-power.description=FastAPI Application Server with Admin"

  # ==================== DATABASE ADMIN UI ====================
  adminer:
    image: adminer:latest
    container_name: ai-adminer
    hostname: adminer
    ports:
      - "8080:8080"
    environment:
      - ADMINER_DEFAULT_SERVER=postgres
      - ADMINER_DESIGN=nette
    networks:
      - ai-system-net
    depends_on:
      - postgres
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 256M
    labels:
      - "com.ai-power.service=admin-ui"
      - "com.ai-power.description=Adminer Database Administration"

# ==================== NETWORKS ====================
networks:
  ai-system-net:
    name: ai-system-network
    driver: bridge
    ipam:
      driver: default
      config:
        - subnet: 172.28.0.0/16
          gateway: 172.28.0.1

# ==================== VOLUMES ====================
volumes:
  ollama_data:
    name: ai-power-ollama-data
    driver: local
  neo4j_data:
    name: ai-power-neo4j-data
    driver: local
  neo4j_logs:
    name: ai-power-neo4j-logs
    driver: local
  neo4j_plugins:
    name: ai-power-neo4j-plugins
    driver: local
  qdrant_data:
    name: ai-power-qdrant-data
    driver: local
  postgres_data:
    name: ai-power-postgres-data
    driver: local
  redis_data:
    name: ai-power-redis-data
    driver: local
  n8n_data:
    name: ai-power-n8n-data
    driver: local
  app_data:
    name: ai-power-app-data
    driver: local
```

---

## Step 5: Application Server Setup

### Create `app/Dockerfile`

```dockerfile
# ============================================================
# AI POWER SYSTEM - APPLICATION SERVER DOCKERFILE
# ============================================================

FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy requirements first (for Docker cache optimization)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Create `app/requirements.txt`

```txt
# ============================================================
# AI POWER SYSTEM - PYTHON DEPENDENCIES
# ============================================================

# Web Framework
fastapi==0.115.0
uvicorn[standard]==0.32.0
python-multipart==0.0.17

# Database - PostgreSQL
sqlalchemy==2.0.36
asyncpg==0.30.0
psycopg2-binary==2.9.10
alembic==1.14.0

# Database - Redis
redis==5.2.0

# Database - Neo4j
neo4j==5.26.0

# Database - Qdrant (Vector)
qdrant-client==1.12.1

# HTTP Client
httpx==0.28.0
aiohttp==3.11.0

# Data Validation
pydantic==2.10.0
pydantic-settings==2.6.0

# Templating
jinja2==3.1.4

# Admin Interface
sqladmin==0.19.0

# Security
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4

# Utilities
python-dotenv==1.0.1
orjson==3.10.11

# AI/ML (Optional - for local processing)
# numpy==1.26.4
# sentence-transformers==2.7.0
```

### Create `app/src/main.py`

```python
"""
AI Power System - Main Application Server
==========================================
FastAPI application that connects all services:
- Ollama (AI Model)
- Neo4j (Graph Database)
- Qdrant (Vector Database)
- PostgreSQL (Relational Database)
- Redis (Cache)
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any
import httpx
from neo4j import GraphDatabase
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
import redis
import os
import logging
from datetime import datetime

# ============================================================
# CONFIGURATION
# ============================================================

class Settings:
    """Application configuration from environment variables"""
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Neo4j
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "password")
    
    # Qdrant
    QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))
    
    # Ollama
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    # Application
    APP_DEBUG: bool = os.getenv("APP_DEBUG", "false").lower() == "true"
    APP_LOG_LEVEL: str = os.getenv("APP_LOG_LEVEL", "INFO")

settings = Settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.APP_LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================
# SERVICE CONNECTIONS
# ============================================================

class ServiceConnections:
    """Manages connections to all external services"""
    neo4j_driver = None
    qdrant_client: Optional[QdrantClient] = None
    redis_client: Optional[redis.Redis] = None

connections = ServiceConnections()

async def init_neo4j():
    """Initialize Neo4j connection"""
    try:
        connections.neo4j_driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
        connections.neo4j_driver.verify_connectivity()
        logger.info("✅ Neo4j connected successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Neo4j connection failed: {e}")
        return False

async def init_qdrant():
    """Initialize Qdrant connection"""
    try:
        connections.qdrant_client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT
        )
        connections.qdrant_client.get_collections()
        logger.info("✅ Qdrant connected successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Qdrant connection failed: {e}")
        return False

async def init_redis():
    """Initialize Redis connection"""
    try:
        connections.redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True
        )
        connections.redis_client.ping()
        logger.info("✅ Redis connected successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        return False

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler - startup and shutdown"""
    # ===== STARTUP =====
    logger.info("🚀 Starting AI Power System...")
    
    await init_neo4j()
    await init_qdrant()
    await init_redis()
    
    logger.info("✅ AI Power System started successfully")
    
    yield
    
    # ===== SHUTDOWN =====
    logger.info("🛑 Shutting down AI Power System...")
    
    if connections.neo4j_driver:
        connections.neo4j_driver.close()
        logger.info("Neo4j connection closed")
    
    if connections.redis_client:
        connections.redis_client.close()
        logger.info("Redis connection closed")
    
    logger.info("👋 AI Power System shutdown complete")

# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="AI Power System",
    description="Unified AI Knowledge Platform with Graph DB, Vector DB, and Local LLM",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# HEALTH CHECK ENDPOINTS
# ============================================================

@app.get("/", tags=["General"])
async def root():
    """Root endpoint with navigation links"""
    return {
        "name": "AI Power System",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "admin": "/admin",
            "api": {
                "ai": "/api/ai",
                "graph": "/api/graph",
                "vector": "/api/vector"
            }
        }
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Comprehensive health check for all services"""
    status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }
    
    # Check Neo4j
    try:
        if connections.neo4j_driver:
            connections.neo4j_driver.verify_connectivity()
            status["services"]["neo4j"] = {"status": "healthy", "uri": settings.NEO4J_URI}
        else:
            status["services"]["neo4j"] = {"status": "not_initialized"}
    except Exception as e:
        status["services"]["neo4j"] = {"status": "unhealthy", "error": str(e)}
        status["status"] = "degraded"
    
    # Check Qdrant
    try:
        if connections.qdrant_client:
            collections = connections.qdrant_client.get_collections()
            status["services"]["qdrant"] = {
                "status": "healthy",
                "collections": len(collections.collections)
            }
        else:
            status["services"]["qdrant"] = {"status": "not_initialized"}
    except Exception as e:
        status["services"]["qdrant"] = {"status": "unhealthy", "error": str(e)}
        status["status"] = "degraded"
    
    # Check Redis
    try:
        if connections.redis_client:
            connections.redis_client.ping()
            info = connections.redis_client.info("memory")
            status["services"]["redis"] = {
                "status": "healthy",
                "used_memory": info.get("used_memory_human", "unknown")
            }
        else:
            status["services"]["redis"] = {"status": "not_initialized"}
    except Exception as e:
        status["services"]["redis"] = {"status": "unhealthy", "error": str(e)}
        status["status"] = "degraded"
    
    # Check Ollama
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                status["services"]["ollama"] = {
                    "status": "healthy",
                    "models_loaded": len(models)
                }
            else:
                status["services"]["ollama"] = {"status": "unhealthy", "code": response.status_code}
    except Exception as e:
        status["services"]["ollama"] = {"status": "unreachable", "error": str(e)}
        status["status"] = "degraded"
    
    return status

# ============================================================
# AI ENDPOINTS (OLLAMA)
# ============================================================

@app.get("/api/ai/models", tags=["AI"])
async def list_ai_models():
    """List all available Ollama models"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Ollama service unavailable: {e}")

@app.post("/api/ai/generate", tags=["AI"])
async def generate_text(request: Dict[str, Any]):
    """Generate text using local Ollama model"""
    prompt = request.get("prompt", "")
    model = request.get("model", "llama3.2:3b")
    
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False
                }
            )
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request timeout - model may still be loading")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Ollama service error: {e}")

@app.post("/api/ai/chat", tags=["AI"])
async def chat_with_ai(request: Dict[str, Any]):
    """Chat conversation with local Ollama model"""
    messages = request.get("messages", [])
    model = request.get("model", "llama3.2:3b")
    
    if not messages:
        raise HTTPException(status_code=400, detail="Messages array is required")
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False
                }
            )
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Ollama service error: {e}")

@app.post("/api/ai/embeddings", tags=["AI"])
async def create_embeddings(request: Dict[str, Any]):
    """Create embeddings using local Ollama model"""
    text = request.get("text", "")
    model = request.get("model", "nomic-embed-text")
    
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/embeddings",
                json={
                    "model": model,
                    "prompt": text
                }
            )
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Ollama service error: {e}")

# ============================================================
# GRAPH DATABASE ENDPOINTS (NEO4J)
# ============================================================

@app.get("/api/graph/stats", tags=["Graph Database"])
async def get_graph_stats():
    """Get Neo4j database statistics"""
    if not connections.neo4j_driver:
        raise HTTPException(status_code=503, detail="Neo4j not connected")
    
    try:
        with connections.neo4j_driver.session() as session:
            # Get node count
            node_result = session.run("MATCH (n) RETURN count(n) as count")
            node_count = node_result.single()["count"]
            
            # Get relationship count
            rel_result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            rel_count = rel_result.single()["count"]
            
            # Get labels
            labels_result = session.run("CALL db.labels() YIELD label RETURN collect(label) as labels")
            labels = labels_result.single()["labels"]
            
            # Get relationship types
            types_result = session.run("CALL db.relationshipTypes() YIELD relationshipType RETURN collect(relationshipType) as types")
            rel_types = types_result.single()["types"]
            
            return {
                "node_count": node_count,
                "relationship_count": rel_count,
                "labels": labels,
                "relationship_types": rel_types
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Neo4j query error: {e}")

@app.post("/api/graph/query", tags=["Graph Database"])
async def execute_cypher_query(request: Dict[str, Any]):
    """Execute a Cypher query on Neo4j"""
    query = request.get("query", "")
    params = request.get("params", {})
    
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")
    
    if not connections.neo4j_driver:
        raise HTTPException(status_code=503, detail="Neo4j not connected")
    
    try:
        with connections.neo4j_driver.session() as session:
            result = session.run(query, params)
            records = [dict(record) for record in result]
            return {"records": records, "count": len(records)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cypher query error: {e}")

# ============================================================
# VECTOR DATABASE ENDPOINTS (QDRANT)
# ============================================================

@app.get("/api/vector/collections", tags=["Vector Database"])
async def list_vector_collections():
    """List all Qdrant collections"""
    if not connections.qdrant_client:
        raise HTTPException(status_code=503, detail="Qdrant not connected")
    
    try:
        collections = connections.qdrant_client.get_collections()
        return {
            "collections": [
                {
                    "name": c.name,
                }
                for c in collections.collections
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Qdrant error: {e}")

@app.post("/api/vector/collections", tags=["Vector Database"])
async def create_vector_collection(request: Dict[str, Any]):
    """Create a new Qdrant collection"""
    name = request.get("name", "")
    vector_size = request.get("vector_size", 384)
    distance = request.get("distance", "cosine")
    
    if not name:
        raise HTTPException(status_code=400, detail="Collection name is required")
    
    if not connections.qdrant_client:
        raise HTTPException(status_code=503, detail="Qdrant not connected")
    
    distance_map = {
        "cosine": Distance.COSINE,
        "euclidean": Distance.EUCLID,
        "dot": Distance.DOT
    }
    
    try:
        connections.qdrant_client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=distance_map.get(distance, Distance.COSINE)
            )
        )
        return {"status": "created", "collection": name, "vector_size": vector_size}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create collection: {e}")

@app.get("/api/vector/collections/{name}", tags=["Vector Database"])
async def get_collection_info(name: str):
    """Get information about a specific collection"""
    if not connections.qdrant_client:
        raise HTTPException(status_code=503, detail="Qdrant not connected")
    
    try:
        info = connections.qdrant_client.get_collection(name)
        return {
            "name": name,
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
            "status": info.status.value
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Collection not found: {e}")

# ============================================================
# CACHE ENDPOINTS (REDIS)
# ============================================================

@app.get("/api/cache/stats", tags=["Cache"])
async def get_cache_stats():
    """Get Redis cache statistics"""
    if not connections.redis_client:
        raise HTTPException(status_code=503, detail="Redis not connected")
    
    try:
        info = connections.redis_client.info()
        return {
            "used_memory": info.get("used_memory_human"),
            "connected_clients": info.get("connected_clients"),
            "total_commands_processed": info.get("total_commands_processed"),
            "keyspace_hits": info.get("keyspace_hits"),
            "keyspace_misses": info.get("keyspace_misses"),
            "uptime_seconds": info.get("uptime_in_seconds")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis error: {e}")

# ============================================================
# ADMIN DASHBOARD
# ============================================================

@app.get("/admin", response_class=HTMLResponse, tags=["Admin"])
async def admin_dashboard():
    """Admin dashboard with service overview"""
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI Power System - Admin Dashboard</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                min-height: 100vh;
                color: #e4e4e4;
            }
            .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
            header { 
                background: rgba(255,255,255,0.05); 
                padding: 20px 30px; 
                border-radius: 12px;
                margin-bottom: 30px;
                backdrop-filter: blur(10px);
            }
            h1 { 
                font-size: 28px; 
                background: linear-gradient(90deg, #00d4ff, #7b2cbf);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            .subtitle { color: #888; margin-top: 5px; }
            .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
            .card { 
                background: rgba(255,255,255,0.05); 
                border-radius: 12px; 
                padding: 24px;
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255,255,255,0.1);
                transition: transform 0.2s, box-shadow 0.2s;
            }
            .card:hover { 
                transform: translateY(-2px); 
                box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            }
            .card h2 { 
                font-size: 18px; 
                margin-bottom: 15px;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            .card h2 span { font-size: 24px; }
            .status { 
                display: inline-flex;
                align-items: center;
                padding: 6px 14px; 
                border-radius: 20px; 
                font-size: 13px;
                font-weight: 500;
                gap: 6px;
            }
            .status.healthy { background: rgba(46, 204, 113, 0.2); color: #2ecc71; }
            .status.unhealthy { background: rgba(231, 76, 60, 0.2); color: #e74c3c; }
            .status.loading { background: rgba(241, 196, 15, 0.2); color: #f1c40f; }
            .status::before { content: '●'; font-size: 10px; }
            .links { margin-top: 15px; }
            .links a { 
                display: inline-block;
                color: #00d4ff; 
                text-decoration: none;
                padding: 8px 16px;
                background: rgba(0,212,255,0.1);
                border-radius: 6px;
                margin: 4px 4px 4px 0;
                font-size: 13px;
                transition: background 0.2s;
            }
            .links a:hover { background: rgba(0,212,255,0.2); }
            .stats { 
                display: grid; 
                grid-template-columns: repeat(2, 1fr); 
                gap: 10px; 
                margin-top: 15px;
            }
            .stat { 
                background: rgba(0,0,0,0.2); 
                padding: 12px; 
                border-radius: 8px;
                text-align: center;
            }
            .stat-value { font-size: 24px; font-weight: bold; color: #00d4ff; }
            .stat-label { font-size: 12px; color: #888; margin-top: 4px; }
            table { width: 100%; border-collapse: collapse; margin-top: 15px; }
            th, td { 
                padding: 12px; 
                text-align: left; 
                border-bottom: 1px solid rgba(255,255,255,0.1);
            }
            th { color: #888; font-weight: 500; font-size: 13px; }
            td a { color: #00d4ff; text-decoration: none; }
            td a:hover { text-decoration: underline; }
            .refresh-btn {
                background: rgba(0,212,255,0.2);
                border: none;
                color: #00d4ff;
                padding: 10px 20px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 14px;
                transition: background 0.2s;
            }
            .refresh-btn:hover { background: rgba(0,212,255,0.3); }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>🚀 AI Power System</h1>
                <p class="subtitle">Unified Knowledge Platform - Admin Dashboard</p>
            </header>
            
            <div class="grid">
                <!-- Service Status Card -->
                <div class="card" style="grid-column: span 2;">
                    <h2><span>📊</span> Service Status <button class="refresh-btn" onclick="loadHealth()">↻ Refresh</button></h2>
                    <div id="services" class="grid">
                        <div class="stat"><div class="stat-value">-</div><div class="stat-label">Loading...</div></div>
                    </div>
                </div>
                
                <!-- Quick Links Card -->
                <div class="card">
                    <h2><span>🔗</span> Quick Links</h2>
                    <table>
                        <tr><th>Service</th><th>URL</th></tr>
                        <tr><td>API Documentation</td><td><a href="/docs" target="_blank">Open Swagger UI →</a></td></tr>
                        <tr><td>Neo4j Browser</td><td><a href="http://localhost:7474" target="_blank">localhost:7474 →</a></td></tr>
                        <tr><td>n8n Automation</td><td><a href="http://localhost:5678" target="_blank">localhost:5678 →</a></td></tr>
                        <tr><td>Database Admin</td><td><a href="http://localhost:8080" target="_blank">localhost:8080 →</a></td></tr>
                        <tr><td>Qdrant Dashboard</td><td><a href="http://localhost:6333/dashboard" target="_blank">localhost:6333 →</a></td></tr>
                    </table>
                </div>
                
                <!-- AI Models Card -->
                <div class="card">
                    <h2><span>🤖</span> AI Models</h2>
                    <div id="models">
                        <p style="color: #888;">Loading models...</p>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            async function loadHealth() {
                try {
                    const response = await fetch('/health');
                    const data = await response.json();
                    
                    let html = '';
                    for (const [service, info] of Object.entries(data.services)) {
                        const status = typeof info === 'object' ? info.status : info;
                        const statusClass = status === 'healthy' ? 'healthy' : 'unhealthy';
                        html += `
                            <div class="stat">
                                <div class="status ${statusClass}">${status}</div>
                                <div class="stat-label" style="margin-top: 8px; text-transform: uppercase;">${service}</div>
                            </div>
                        `;
                    }
                    document.getElementById('services').innerHTML = html;
                } catch (e) {
                    document.getElementById('services').innerHTML = '<p style="color: #e74c3c;">Failed to load health status</p>';
                }
            }
            
            async function loadModels() {
                try {
                    const response = await fetch('/api/ai/models');
                    const data = await response.json();
                    
                    if (data.models && data.models.length > 0) {
                        let html = '<ul style="list-style: none;">';
                        for (const model of data.models) {
                            const size = (model.size / 1e9).toFixed(1);
                            html += `<li style="padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.1);">
                                <strong>${model.name}</strong>
                                <span style="color: #888; font-size: 12px; margin-left: 10px;">${size} GB</span>
                            </li>`;
                        }
                        html += '</ul>';
                        document.getElementById('models').innerHTML = html;
                    } else {
                        document.getElementById('models').innerHTML = '<p style="color: #888;">No models loaded. Run: <code>docker exec ai-ollama ollama pull llama3.2:3b</code></p>';
                    }
                } catch (e) {
                    document.getElementById('models').innerHTML = '<p style="color: #888;">Ollama not available</p>';
                }
            }
            
            // Load data on page load
            loadHealth();
            loadModels();
            
            // Auto-refresh every 30 seconds
            setInterval(loadHealth, 30000);
        </script>
    </body>
    </html>
    """
    return html

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
            "detail": str(exc) if settings.APP_DEBUG else "An unexpected error occurred"
        }
    )

# ============================================================
# MAIN ENTRY POINT
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.APP_DEBUG
    )
```

---

## Step 6: Database Initialization

### Create `postgres/init/init.sql`

```sql
-- ============================================================
-- AI POWER SYSTEM - DATABASE INITIALIZATION
-- ============================================================
-- This script runs automatically when PostgreSQL container starts
-- for the first time (empty data directory)
-- ============================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- ============================================================
-- N8N SCHEMA (for n8n workflow automation)
-- ============================================================
CREATE SCHEMA IF NOT EXISTS n8n;

-- ============================================================
-- APPLICATION TABLES
-- ============================================================

-- Documents table for storing processed documents
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    content TEXT,
    content_type VARCHAR(100) DEFAULT 'text/plain',
    file_path VARCHAR(1000),
    file_size BIGINT,
    metadata JSONB DEFAULT '{}',
    embedding_id VARCHAR(255),
    neo4j_node_id VARCHAR(255),
    checksum VARCHAR(64),
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Entities extracted from documents
CREATE TABLE IF NOT EXISTS entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(500) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    description TEXT,
    properties JSONB DEFAULT '{}',
    neo4j_node_id VARCHAR(255),
    source_document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    confidence DECIMAL(5,4) DEFAULT 1.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Relationships between entities
CREATE TABLE IF NOT EXISTS relationships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_entity_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    target_entity_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    relationship_type VARCHAR(100) NOT NULL,
    properties JSONB DEFAULT '{}',
    neo4j_rel_id VARCHAR(255),
    weight DECIMAL(5,4) DEFAULT 1.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    is_verified BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- API Keys for external access
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    key_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    permissions JSONB DEFAULT '["read"]',
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Query history for analytics
CREATE TABLE IF NOT EXISTS query_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    query_text TEXT NOT NULL,
    query_type VARCHAR(50) NOT NULL,
    response_summary TEXT,
    execution_time_ms INTEGER,
    tokens_used INTEGER,
    model_used VARCHAR(100),
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- System configuration
CREATE TABLE IF NOT EXISTS system_config (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by UUID REFERENCES users(id)
);

-- ============================================================
-- INDEXES
-- ============================================================

-- Documents indexes
CREATE INDEX idx_documents_title_trgm ON documents USING gin(title gin_trgm_ops);
CREATE INDEX idx_documents_content_trgm ON documents USING gin(content gin_trgm_ops);
CREATE INDEX idx_documents_metadata ON documents USING gin(metadata);
CREATE INDEX idx_documents_processed ON documents(processed);
CREATE INDEX idx_documents_created_at ON documents(created_at DESC);

-- Entities indexes
CREATE INDEX idx_entities_name ON entities(name);
CREATE INDEX idx_entities_name_trgm ON entities USING gin(name gin_trgm_ops);
CREATE INDEX idx_entities_type ON entities(entity_type);
CREATE INDEX idx_entities_properties ON entities USING gin(properties);

-- Relationships indexes
CREATE INDEX idx_relationships_source ON relationships(source_entity_id);
CREATE INDEX idx_relationships_target ON relationships(target_entity_id);
CREATE INDEX idx_relationships_type ON relationships(relationship_type);

-- Users indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);

-- Query history indexes
CREATE INDEX idx_query_history_user ON query_history(user_id);
CREATE INDEX idx_query_history_created ON query_history(created_at DESC);
CREATE INDEX idx_query_history_type ON query_history(query_type);

-- ============================================================
-- FUNCTIONS
-- ============================================================

-- Auto-update timestamp function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- ============================================================
-- TRIGGERS
-- ============================================================

-- Auto-update timestamps
CREATE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_system_config_updated_at
    BEFORE UPDATE ON system_config
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- INITIAL DATA
-- ============================================================

-- Insert default system configuration
INSERT INTO system_config (key, value, description) VALUES
    ('ai_default_model', '"llama3.2:3b"', 'Default AI model for text generation'),
    ('embedding_model', '"nomic-embed-text"', 'Model used for creating embeddings'),
    ('vector_dimensions', '384', 'Dimension of embedding vectors'),
    ('max_tokens', '4096', 'Maximum tokens for AI generation'),
    ('system_version', '"1.0.0"', 'Current system version')
ON CONFLICT (key) DO NOTHING;

-- ============================================================
-- PERMISSIONS
-- ============================================================

-- Grant permissions to application user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO aipower;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO aipower;
GRANT ALL PRIVILEGES ON SCHEMA n8n TO aipower;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA n8n TO aipower;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA n8n TO aipower;

-- ============================================================
-- COMPLETION MESSAGE
-- ============================================================
DO $$
BEGIN
    RAISE NOTICE '✅ AI Power System database initialized successfully!';
END $$;
```

---

## Step 7: Deployment Commands

### Initial Setup & Start

```bash
# Navigate to project directory
cd ai-power-system

# Create environment file from template
cp .env.example .env
# Edit .env with your secure passwords
nano .env

# Build and start all services
docker compose up -d --build

# View real-time logs
docker compose logs -f

# Check all service status
docker compose ps
```

### Pull AI Models (First Time)

```bash
# Pull the main conversational model
docker exec ai-ollama ollama pull llama3.2:3b

# Pull embedding model for vector search
docker exec ai-ollama ollama pull nomic-embed-text

# (Optional) Pull additional models
docker exec ai-ollama ollama pull qwen2.5:7b
docker exec ai-ollama ollama pull codellama:7b

# Verify installed models
docker exec ai-ollama ollama list
```

### Verify All Services

```bash
# Check application server
curl http://localhost:8000/
curl http://localhost:8000/health

# Check Ollama
curl http://localhost:11434/api/tags

# Check Neo4j
curl http://localhost:7474

# Check Qdrant
curl http://localhost:6333/health

# Check n8n (will redirect to login)
curl -I http://localhost:5678

# Check Redis
docker exec ai-redis redis-cli ping
```

### One-Line Health Check Script

```bash
#!/bin/bash
echo "=== AI Power System Health Check ==="
echo ""
echo "App Server:  $(curl -s http://localhost:8000/health | jq -r '.status' 2>/dev/null || echo 'FAILED')"
echo "Ollama:      $(curl -s http://localhost:11434/api/tags > /dev/null && echo 'OK' || echo 'FAILED')"
echo "Neo4j:       $(curl -s http://localhost:7474 > /dev/null && echo 'OK' || echo 'FAILED')"
echo "Qdrant:      $(curl -s http://localhost:6333/health | jq -r '.status' 2>/dev/null || echo 'FAILED')"
echo "Redis:       $(docker exec ai-redis redis-cli ping 2>/dev/null || echo 'FAILED')"
echo "PostgreSQL:  $(docker exec ai-postgres pg_isready -U aipower > /dev/null 2>&1 && echo 'OK' || echo 'FAILED')"
```

---

## Step 8: Service Access Summary

| Service | URL | Default Credentials | Description |
|---------|-----|---------------------|-------------|
| **Application API** | http://localhost:8000 | - | Main API server |
| **API Documentation** | http://localhost:8000/docs | - | Swagger/OpenAPI docs |
| **Admin Dashboard** | http://localhost:8000/admin | - | System overview |
| **Neo4j Browser** | http://localhost:7474 | neo4j / (your password) | Graph database UI |
| **n8n Automation** | http://localhost:5678 | admin / (your password) | Workflow automation |
| **Adminer** | http://localhost:8080 | aipower / (your password) | Database admin UI |
| **Ollama API** | http://localhost:11434 | - | AI model API |
| **Qdrant Dashboard** | http://localhost:6333/dashboard | - | Vector DB UI |

### Service Ports Overview

```
┌────────────────────────────────────────────────────────────┐
│                    PORT MAPPING                            │
├────────────────────────────────────────────────────────────┤
│  8000  │ Application Server (FastAPI)                      │
│  8080  │ Adminer (Database Admin)                          │
│  5678  │ n8n Automation                                    │
│  7474  │ Neo4j Browser (HTTP)                              │
│  7687  │ Neo4j Bolt Protocol                               │
│  6333  │ Qdrant REST API                                   │
│  6334  │ Qdrant gRPC                                       │
│  11434 │ Ollama API                                        │
│  5432  │ PostgreSQL                                        │
│  6379  │ Redis                                             │
└────────────────────────────────────────────────────────────┘
```

---

## Step 9: Common Operations

### Service Management

```bash
# Stop all services
docker compose down

# Stop and remove volumes (⚠️ deletes all data)
docker compose down -v

# Restart specific service
docker compose restart app
docker compose restart neo4j
docker compose restart n8n

# Rebuild and restart a service
docker compose up -d --build app

# Scale a service (stateless only)
docker compose up -d --scale app=3

# View service logs
docker compose logs -f app
docker compose logs -f neo4j
docker compose logs --tail=100 n8n
```

### Data Management

```bash
# Backup PostgreSQL
docker exec ai-postgres pg_dump -U aipower aipower_db > backup_$(date +%Y%m%d).sql

# Restore PostgreSQL
cat backup_20241101.sql | docker exec -i ai-postgres psql -U aipower aipower_db

# Backup Neo4j
docker exec ai-neo4j neo4j-admin database dump --to-stdout neo4j > neo4j_backup.dump

# Restore Neo4j
cat neo4j_backup.dump | docker exec -i ai-neo4j neo4j-admin database load --from-stdin neo4j

# Export Qdrant collection
curl -X GET "http://localhost:6333/collections/my_collection/points/scroll" \
  -H "Content-Type: application/json" > qdrant_backup.json

# List Docker volumes
docker volume ls | grep ai-power

# Backup all volumes (using docker-volume-backup or similar)
for vol in $(docker volume ls -q | grep ai-power); do
  docker run --rm -v $vol:/data -v $(pwd)/backups:/backup alpine \
    tar czf /backup/$vol.tar.gz -C /data .
done
```

### Monitoring & Debugging

```bash
# View container resource usage
docker stats

# View container details
docker inspect ai-app-server

# Execute command in container
docker exec -it ai-app-server bash
docker exec -it ai-postgres psql -U aipower -d aipower_db
docker exec -it ai-redis redis-cli
docker exec -it ai-neo4j cypher-shell -u neo4j -p your_password

# View Docker network
docker network inspect ai-system-network

# Check disk usage
docker system df
docker system df -v
```

### Cleanup Commands

```bash
# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune

# Remove all unused resources
docker system prune -a

# Remove specific stopped containers
docker rm $(docker ps -aq -f status=exited)
```

---

## Resource Usage Estimate

### Memory Allocation

| Service | RAM (Limit) | RAM (Reserved) | Notes |
|---------|-------------|----------------|-------|
| Ollama | 8 GB | 4 GB | Varies by model size |
| Neo4j | 4 GB | 2 GB | Heap + Page Cache |
| Qdrant | 4 GB | 2 GB | Depends on vector count |
| PostgreSQL | 2 GB | 1 GB | Connection pooling recommended |
| Redis | 1 GB | 512 MB | In-memory cache |
| n8n | 2 GB | 1 GB | Depends on workflow complexity |
| App Server | 2 GB | 1 GB | FastAPI application |
| Adminer | 256 MB | - | Lightweight |
| **Total** | **~23 GB** | **~12 GB** | - |

### Disk Space Requirements

| Component | Estimated Size | Notes |
|-----------|---------------|-------|
| Docker Images | ~10 GB | All service images |
| Ollama Models | 5-50 GB | Depends on models downloaded |
| Neo4j Data | Variable | ~1GB per 1M nodes |
| Qdrant Data | Variable | ~1GB per 1M vectors |
| PostgreSQL Data | Variable | Depends on usage |
| **Minimum Total** | **~25 GB** | For basic setup |
| **Recommended** | **100+ GB** | For production use |

### CPU Recommendations

| Workload | Minimum | Recommended |
|----------|---------|-------------|
| Development | 4 cores | 8 cores |
| Light Production | 8 cores | 16 cores |
| Heavy Production | 16 cores | 32+ cores |

---

## Troubleshooting

### Common Issues & Solutions

#### 1. Services Not Starting

```bash
# Check container logs
docker compose logs <service-name>

# Check if ports are in use
sudo lsof -i :8000
sudo lsof -i :7474

# Verify Docker resources
docker system info
```

#### 2. Database Connection Issues

```bash
# Test PostgreSQL connection
docker exec ai-postgres pg_isready -U aipower

# Check PostgreSQL logs
docker compose logs postgres

# Verify network connectivity
docker exec ai-app-server ping postgres
```

#### 3. Neo4j Memory Issues

```bash
# Adjust memory settings in docker-compose.yml
# NEO4J_server_memory_heap_max__size=1G  # Reduce if needed

# Check Neo4j status
docker exec ai-neo4j neo4j status
```

#### 4. Ollama Model Loading Issues

```bash
# Check available space
docker exec ai-ollama df -h

# List downloaded models
docker exec ai-ollama ollama list

# Remove a model to free space
docker exec ai-ollama ollama rm <model-name>

# Re-pull model
docker exec ai-ollama ollama pull llama3.2:3b
```

#### 5. n8n Workflow Issues

```bash
# Check n8n logs
docker compose logs n8n

# Reset n8n (⚠️ deletes workflows)
docker compose down
docker volume rm ai-power-n8n-data
docker compose up -d n8n
```

#### 6. Container Communication Issues

```bash
# Verify network
docker network inspect ai-system-network

# Test inter-container connectivity
docker exec ai-app-server curl http://neo4j:7474
docker exec ai-app-server curl http://qdrant:6333/health
```

### Reset Everything (Fresh Start)

```bash
# Stop all containers
docker compose down

# Remove all volumes (⚠️ DELETES ALL DATA)
docker compose down -v

# Remove all images
docker compose down --rmi all

# Clean Docker system
docker system prune -a --volumes

# Rebuild from scratch
docker compose up -d --build
```

---

## Next Steps

After successful deployment:

1. **Configure n8n workflows**
   - Connect to your data sources
   - Set up ETL pipelines
   - Create automation triggers

2. **Design Neo4j schema**
   - Define node labels
   - Create relationship types
   - Set up indexes and constraints

3. **Set up Qdrant collections**
   - Create collections for different data types
   - Configure vector dimensions
   - Set up payload schemas

4. **Integrate external APIs**
   - Add Claude API for enhanced AI
   - Connect external data sources
   - Set up webhooks

5. **Production hardening**
   - Add SSL/TLS certificates
   - Configure proper authentication
   - Set up monitoring (Prometheus/Grafana)
   - Implement backup strategies

---

## Quick Reference Commands

```bash
# Start system
docker compose up -d

# Stop system
docker compose down

# View status
docker compose ps

# View logs
docker compose logs -f

# Restart service
docker compose restart <service>

# Health check
curl http://localhost:8000/health

# Pull AI model
docker exec ai-ollama ollama pull llama3.2:3b

# Access Neo4j shell
docker exec -it ai-neo4j cypher-shell

# Access PostgreSQL shell
docker exec -it ai-postgres psql -U aipower -d aipower_db

# Access Redis CLI
docker exec -it ai-redis redis-cli
```

---

## Document Information

| Property | Value |
|----------|-------|
| **Version** | 1.0 |
| **Last Updated** | November 2025 |
| **Author** | VXIP Technical Team |
| **Project** | AI Power System - Smart Knowledge Warehouse |

---

*For additional support or questions, refer to the project documentation or contact the technical team.*
