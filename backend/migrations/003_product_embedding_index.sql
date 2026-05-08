-- IVFFlat index on products.embedding for fast semantic search
-- Requires products with embeddings to be vaccumed first for optimal performance
CREATE INDEX IF NOT EXISTS idx_products_embedding_ivfflat
  ON products
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
