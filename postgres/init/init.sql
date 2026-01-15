-- ============================================================
-- AI POWER SYSTEM - DATABASE INITIALIZATION
-- ============================================================
-- Runs automatically when PostgreSQL container starts
-- ============================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ============================================================
-- N8N SCHEMA
-- ============================================================
CREATE SCHEMA IF NOT EXISTS n8n;

-- ============================================================
-- DOCUMENTS TABLE
-- ============================================================
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
    progress INTEGER DEFAULT 0,
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

-- ============================================================
-- CHUNKS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding_id VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- CHAT HISTORY TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS chat_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    sources JSONB DEFAULT '[]',
    model VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- USERS TABLE
-- ============================================================
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

-- ============================================================
-- SYSTEM CONFIG TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS system_config (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- INDEXES
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_created ON documents(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_documents_name ON documents USING gin(name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_documents_tags ON documents USING gin(tags);
CREATE INDEX IF NOT EXISTS idx_documents_language ON documents(language);

CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks(embedding_id);

CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_history(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_created ON chat_history(created_at DESC);

-- ============================================================
-- UPDATE TRIGGER
-- ============================================================
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

-- ============================================================
-- INITIAL CONFIG
-- ============================================================
INSERT INTO system_config (key, value, description) VALUES
    ('default_model', '"llama3.2:3b"', 'Default AI model'),
    ('embedding_model', '"nomic-embed-text"', 'Embedding model'),
    ('chunk_size', '1000', 'Document chunk size'),
    ('chunk_overlap', '200', 'Chunk overlap'),
    ('version', '"1.0.0"', 'System version')
ON CONFLICT (key) DO NOTHING;

-- ============================================================
-- PERMISSIONS
-- ============================================================
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO aipower;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO aipower;
GRANT ALL PRIVILEGES ON SCHEMA n8n TO aipower;

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✅ AI Power System database initialized!';
END $$;


