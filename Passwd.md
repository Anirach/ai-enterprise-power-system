# AI Power System - Service Credentials

## PostgreSQL Database
- **Host:** `localhost:5432` (external) / `postgres:5432` (internal)
- **Database:** `aipower_db`
- **Username:** `aipower`
- **Password:** `aipower_secure_password_2024`

## pgAdmin (PostgreSQL Admin Panel)
- **URL:** http://localhost:5050
- **Email:** `admin@example.com`
- **Password:** `admin123`
- **PostgreSQL Connection:**
  - Host: `postgres`
  - Port: `5432`
  - Database: `aipower_db`
  - Username: `aipower`
  - Password: `aipower_secure_password_2024`

## MinIO (Object Storage)
- **Console URL:** http://localhost:9001
- **API URL:** http://localhost:9000
- **Username:** `minioadmin`
- **Password:** `minioadmin123`
- **Bucket:** `documents`

## n8n (Workflow Automation)
- **URL:** http://localhost:5678
- **Username:** `admin`
- **Password:** `n8n_admin_2024`

## Redis (Cache)
- **URL:** `redis://localhost:6379`
- **Password:** (none)

## Qdrant (Vector Database)
- **Dashboard URL:** http://localhost:6333/dashboard
- **API URL:** http://localhost:6333
- **Authentication:** (none)

## Ollama (LLM Server)
- **API URL:** http://localhost:11434
- **Default Model:** `llama3.2:3b`
- **Authentication:** (none)

## Backend API (FastAPI)
- **URL:** http://localhost:3602
- **Swagger Docs:** http://localhost:3602/docs
- **Secret Key:** `your_super_secret_key_2024`

## Frontend (Next.js)
- **URL:** http://localhost:3601
- **Authentication:** (none)

---

**Note:** These credentials are for development/local use. Change all passwords before deploying to production.
