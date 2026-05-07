-- Migration: Convert customer embedding column from JSON to pgvector VECTOR(1024)
-- Requires: CREATE EXTENSION vector; (run as superuser)
-- Run with: psql -U your_user -d your_db -f 001_pgvector_embedding.sql

-- 1. Enable the vector extension (skip if already enabled)
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Drop existing data in embedding column (they're JSON arrays, not compatible)
-- Back up first if needed
UPDATE customers SET embedding = NULL WHERE embedding IS NOT NULL;

-- 3. Alter column type: JSON -> vector(1024)
ALTER TABLE customers
  ALTER COLUMN embedding TYPE vector(1024)
  USING NULL;

-- 4. Create IVFFlat index for fast approximate nearest-neighbor search
-- Indexes cosine distance for semantic similarity queries
CREATE INDEX IF NOT EXISTS idx_customers_embedding_ivfflat
  ON customers
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

-- 5. Re-populate embeddings via the API: POST /api/v1/ai/customer/embed-all
-- Or programmatically via EmbeddingService.index_all()
