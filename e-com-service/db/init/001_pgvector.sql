CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS kb_embeddings (
    chunk_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB NOT NULL,
    embedding VECTOR(3072) NOT NULL,
    source TEXT NOT NULL DEFAULT 'product.csv',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_kb_embeddings_doc_id
    ON kb_embeddings (doc_id);

CREATE INDEX IF NOT EXISTS idx_kb_embeddings_metadata_gin
    ON kb_embeddings USING GIN (metadata);

CREATE INDEX IF NOT EXISTS idx_kb_embeddings_vector_cosine
    ON kb_embeddings USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
