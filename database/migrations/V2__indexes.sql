-- Vector similarity index (HNSW — better query performance than IVFFlat)
CREATE INDEX idx_movies_embedding
    ON movies USING hnsw (embedding vector_cosine_ops);

-- Metadata filter indexes for hybrid search
CREATE INDEX idx_movies_genre      ON movies (major_genre);
CREATE INDEX idx_movies_decade     ON movies (decade);
CREATE INDEX idx_movies_mpaa       ON movies (mpaa_rating);
CREATE INDEX idx_movies_imdb       ON movies (imdb_rating);
