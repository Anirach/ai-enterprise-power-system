# AI Power System

All-in-One Docker deployment for AI-powered knowledge management with Local LLM, RAG, and workflow automation.

## Features

- **Chat Interface** - Talk with AI using your knowledge base
- **Knowledge Base** - Upload documents and crawl websites
- **Advanced Document Parsing** - Powered by [Docling](https://github.com/docling-project/docling) (IBM)
  - PDF with table extraction, layout analysis, reading order
  - DOCX, PPTX, XLSX support
  - OCR for scanned documents and images
- **RAG Pipeline** - Retrieval Augmented Generation for accurate answers
- **Local LLM** - Ollama-powered, runs on your machine
- **Admin Dashboard** - Monitor services, manage AI models
- **Workflow Automation** - n8n for custom workflows

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Compose                           │
├─────────────────────────────────────────────────────────────┤
│  Frontend (Next.js)  :3000    │  Backend (FastAPI)  :8000   │
├─────────────────────────────────────────────────────────────┤
│  Ollama :11434  │  Qdrant :6333  │  PostgreSQL :5432        │
│  Redis :6379    │  n8n :5678                                 │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Clone and Setup

```bash
cd ai-power-system
```

### 2. Start Services

```bash
docker compose up -d --build
```

### 3. Pull AI Models

```bash
# Main chat model
docker exec ai-ollama ollama pull llama3.2:3b

# Embedding model for RAG
docker exec ai-ollama ollama pull nomic-embed-text
```

### 4. Access the Application

| Service | URL | Description |
|---------|-----|-------------|
| **Main App** | http://localhost:3000 | Chat & Knowledge Base UI |
| **API Docs** | http://localhost:8000/docs | Swagger API Documentation |
| **n8n** | http://localhost:5678 | Workflow Automation |
| **Qdrant** | http://localhost:6333/dashboard | Vector DB Dashboard |

## Services Overview

| Service | Port | Purpose |
|---------|------|---------|
| Frontend | 3000 | Next.js Web UI |
| Backend | 8000 | FastAPI REST API |
| Ollama | 11434 | Local LLM |
| Qdrant | 6333 | Vector Database |
| PostgreSQL | 5432 | Relational Database |
| Redis | 6379 | Cache |
| n8n | 5678 | Workflow Automation |

## Usage

### Chat with AI

1. Open http://localhost:3000
2. Toggle "Use Knowledge Base" for RAG-powered responses
3. Ask questions - AI will search your documents for context

### Upload Documents

1. Go to "Knowledge Base" page
2. Upload files (supported formats below)
3. Documents are automatically parsed and indexed

**Supported formats (powered by [Docling](https://github.com/docling-project/docling)):**
- PDF (with table extraction, layout analysis)
- DOCX, PPTX, XLSX (Microsoft Office)
- HTML, Images (PNG, JPG, TIFF with OCR)
- TXT, MD, CSV

### Crawl Websites

1. Go to "Knowledge Base" page
2. Enter a URL in the crawl section
3. Content is extracted and added to your knowledge base

### Admin Dashboard

1. Go to "Admin" page
2. View service status
3. Pull/delete AI models
4. Access quick links to all services

## Configuration

Edit `.env` file to customize:

```bash
# AI Models
OLLAMA_DEFAULT_MODEL=llama3.2:3b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# n8n Credentials
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=your_password

# Database
POSTGRES_PASSWORD=your_password
```

## Common Commands

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down

# Restart a service
docker compose restart backend

# Pull new AI model
docker exec ai-ollama ollama pull mistral:7b

# List AI models
docker exec ai-ollama ollama list

# Access PostgreSQL
docker exec -it ai-postgres psql -U aipower -d aipower_db

# Access Redis CLI
docker exec -it ai-redis redis-cli
```

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 16 GB | 32 GB |
| CPU | 4 cores | 8+ cores |
| Storage | 30 GB | 100 GB |
| Docker | 24.0+ | Latest |

## Troubleshooting

### Services not starting

```bash
# Check container status
docker compose ps

# View specific service logs
docker compose logs backend
docker compose logs frontend
```

### AI not responding

```bash
# Check if Ollama has models
docker exec ai-ollama ollama list

# Pull required models
docker exec ai-ollama ollama pull llama3.2:3b
docker exec ai-ollama ollama pull nomic-embed-text
```

### Database connection issues

```bash
# Check PostgreSQL
docker exec ai-postgres pg_isready -U aipower

# Reset database (warning: deletes data)
docker compose down -v
docker compose up -d
```

## Development

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn src.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## License

MIT License
