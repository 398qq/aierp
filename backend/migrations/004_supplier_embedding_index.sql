-- IVFFlat index on suppliers.embedding for fast semantic search
CREATE INDEX IF NOT EXISTS idx_suppliers_embedding_ivfflat
  ON suppliers
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
