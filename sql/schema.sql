-- Recipe RAG Knowledge Graph - PostgreSQL Schema
-- Requires pgvector extension

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- =============================================================================
-- Tables
-- =============================================================================

-- Documents table - stores recipe files
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Chunks table - stores text chunks with embeddings
CREATE TABLE IF NOT EXISTS chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(1536),
    chunk_index INTEGER NOT NULL,
    token_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Sessions table - stores conversation sessions
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

-- Messages table - stores conversation messages
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- Indexes
-- =============================================================================

-- HNSW index for vector similarity search (cosine distance)
-- HNSW works well for any dataset size without requiring tuning like IVFFlat
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks
    USING hnsw (embedding vector_cosine_ops);

-- GIN indexes for JSONB metadata
CREATE INDEX IF NOT EXISTS idx_documents_metadata ON documents USING GIN (metadata);
CREATE INDEX IF NOT EXISTS idx_chunks_metadata ON chunks USING GIN (metadata);

-- Full-text search indexes
CREATE INDEX IF NOT EXISTS idx_documents_content_trgm ON documents USING GIN (content gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_chunks_content_trgm ON chunks USING GIN (content gin_trgm_ops);

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_document_chunk ON chunks(document_id, chunk_index);
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_session_created ON messages(session_id, created_at);

-- =============================================================================
-- Functions
-- =============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
DROP TRIGGER IF EXISTS trigger_documents_updated_at ON documents;
CREATE TRIGGER trigger_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trigger_sessions_updated_at ON sessions;
CREATE TRIGGER trigger_sessions_updated_at
    BEFORE UPDATE ON sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Vector similarity search function
CREATE OR REPLACE FUNCTION match_chunks(
    query_embedding vector(1536),
    match_count INT DEFAULT 10
)
RETURNS TABLE (
    chunk_id UUID,
    document_id UUID,
    document_title TEXT,
    document_source TEXT,
    content TEXT,
    chunk_index INTEGER,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id AS chunk_id,
        c.document_id,
        d.title AS document_title,
        d.source AS document_source,
        c.content,
        c.chunk_index,
        c.metadata,
        1 - (c.embedding <=> query_embedding) AS similarity
    FROM chunks c
    JOIN documents d ON c.document_id = d.id
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Hybrid search function (vector + full-text)
CREATE OR REPLACE FUNCTION hybrid_search(
    query_embedding vector(1536),
    query_text TEXT,
    match_count INT DEFAULT 10,
    text_weight FLOAT DEFAULT 0.3
)
RETURNS TABLE (
    chunk_id UUID,
    document_id UUID,
    document_title TEXT,
    document_source TEXT,
    content TEXT,
    chunk_index INTEGER,
    metadata JSONB,
    vector_score FLOAT,
    text_score FLOAT,
    combined_score FLOAT
)
LANGUAGE plpgsql
AS $$
DECLARE
    vector_weight FLOAT := 1.0 - text_weight;
BEGIN
    RETURN QUERY
    WITH vector_results AS (
        SELECT
            c.id,
            c.document_id,
            d.title AS document_title,
            d.source AS document_source,
            c.content,
            c.chunk_index,
            c.metadata,
            1 - (c.embedding <=> query_embedding) AS v_score
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE c.embedding IS NOT NULL
    ),
    text_results AS (
        SELECT
            c.id,
            similarity(c.content, query_text) AS t_score
        FROM chunks c
        WHERE c.content % query_text
    )
    SELECT
        vr.id AS chunk_id,
        vr.document_id,
        vr.document_title,
        vr.document_source,
        vr.content,
        vr.chunk_index,
        vr.metadata,
        vr.v_score AS vector_score,
        COALESCE(tr.t_score, 0.0)::FLOAT AS text_score,
        (vector_weight * vr.v_score + text_weight * COALESCE(tr.t_score, 0.0))::FLOAT AS combined_score
    FROM vector_results vr
    LEFT JOIN text_results tr ON vr.id = tr.id
    ORDER BY (vector_weight * vr.v_score + text_weight * COALESCE(tr.t_score, 0.0)) DESC
    LIMIT match_count;
END;
$$;

-- Get all chunks for a document in order
CREATE OR REPLACE FUNCTION get_document_chunks(
    doc_id UUID
)
RETURNS TABLE (
    chunk_id UUID,
    content TEXT,
    chunk_index INTEGER,
    metadata JSONB
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id AS chunk_id,
        c.content,
        c.chunk_index,
        c.metadata
    FROM chunks c
    WHERE c.document_id = doc_id
    ORDER BY c.chunk_index;
END;
$$;

-- Get session messages
CREATE OR REPLACE FUNCTION get_session_messages(
    p_session_id UUID,
    p_limit INT DEFAULT 100
)
RETURNS TABLE (
    id UUID,
    role VARCHAR(50),
    content TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.id,
        m.role,
        m.content,
        m.metadata,
        m.created_at
    FROM messages m
    WHERE m.session_id = p_session_id
    ORDER BY m.created_at ASC
    LIMIT p_limit;
END;
$$;

-- =============================================================================
-- Views
-- =============================================================================

-- Document summaries with chunk counts
CREATE OR REPLACE VIEW document_summaries AS
SELECT
    d.id,
    d.title,
    d.source,
    d.metadata,
    d.created_at,
    d.updated_at,
    COUNT(c.id) AS chunk_count,
    SUM(LENGTH(c.content)) AS total_content_length
FROM documents d
LEFT JOIN chunks c ON d.id = c.document_id
GROUP BY d.id, d.title, d.source, d.metadata, d.created_at, d.updated_at;
